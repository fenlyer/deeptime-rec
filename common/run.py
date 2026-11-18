"""运行记录（S1-c）

每次训练或评估都经 start_run 记录到 results/{exp}/{model}/seed{n}/：
    metrics.json    由调用方写（本模块不规定指标名）
    per_user.parquet 由调用方写
    config.yaml      本模块写
    train_log.csv    本模块写（log_epoch 逐轮追加）
    manifest.json    本模块在退出时写

口径
----
    - 工作区有未提交改动时，结果目录前缀改为 _dirty_{exp}，并打印醒目警告：
      正式实验不得在脏工作区上启动（CLAUDE.md 运行规范），脏结果与正式结果
      物理隔离，避免被 make_tables 采集成论文数字。
    - manifest.git_tags 记录 HEAD 上全部 tag，事后可完整回溯数据与实验冻结状态；
      无 tag 时为空列表，不写 null（便于下游判断"有 tag 字段但为空"）。
    - git_dirty_files 记录未提交改动清单，便于事后定位"哪个文件改了导致重跑"。

用法：
    from common.run import start_run

    with start_run("recall_main", "lightgcn", seed=0, config=cfg) as h:
        for epoch in range(1, epochs + 1):
            loss = train_one_epoch(...)
            h.log_epoch(epoch=epoch, loss=loss, seconds=elapsed, n_eval=recall)
        h.set_best_epoch(best_epoch)
        h.set_stop_reason("patience")
        metrics.to_json(h.dir / "metrics.json")
        per_user.to_parquet(h.dir / "per_user.parquet", index=False)
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"


# --------------------------------------------------------------------------- git
def _git(args: list[str]) -> Optional[str]:
    """在仓库根目录执行 git 命令，失败返回 None（不在 git 仓库内或 git 不可用）。"""
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def _git_commit() -> Optional[str]:
    return _git(["rev-parse", "HEAD"])


# 产物目录：这些前缀下的未跟踪文件不算 dirty，否则每跑一次实验都被判 dirty
_OUTPUT_PREFIXES = ("results/", "build/", "artifacts/", "figures/", "thesis/generated/")


def _is_git_dirty() -> tuple[bool, list[str]]:
    """返回 (是否有未提交改动, 改动文件列表)。

    已跟踪文件的任何改动都算 dirty；未跟踪文件里只有源码类算 dirty，
    产物目录（结果、构建、图）下的新文件不算 —— 它们本就是每次运行的产物，
    计入会让所有正式实验都被打上 _dirty_ 前缀，反而失去信号。
    """
    out = _git(["status", "--porcelain"])
    if out is None:
        return False, []
    files: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status = line[:2].strip()
        path = line[3:].strip().split(" -> ")[-1]
        if status == "??" and path.startswith(_OUTPUT_PREFIXES):
            continue
        files.append(path)
    return (len(files) > 0), files


def _git_tags() -> list[str]:
    """HEAD 上的全部 tag。"""
    out = _git(["tag", "--points-at", "HEAD"])
    if not out:
        return []
    return [t.strip() for t in out.splitlines() if t.strip()]


# --------------------------------------------------------------------------- GPU
def _gpu_info() -> Optional[dict]:
    """有 torch 且 CUDA 可用时记录型号；峰值显存由调用方在训练结束后补写。"""
    try:
        import torch
    except ImportError:
        return None
    if not torch.cuda.is_available():
        return None
    try:
        return {
            "name": torch.cuda.get_device_name(0),
            "total_memory_mb": round(
                torch.cuda.get_device_properties(0).total_memory / 1024**2, 1
            ),
        }
    except Exception:  # noqa: BLE001  设备查询失败不应中断训练
        return None


# --------------------------------------------------------------------------- handle
@dataclass
class RunHandle:
    """一次运行的句柄：目录、manifest 字段、逐轮日志。"""

    dir: Path
    exp: str
    model: str
    seed: int
    config: dict
    git_commit: Optional[str]
    git_dirty: bool
    git_dirty_files: list[str]
    git_tags: list[str]
    command: str
    started_at: str
    gpu: Optional[dict]
    epoch_seconds: list[float] = field(default_factory=list)
    best_epoch: Optional[int] = None
    stop_reason: str = "completed"
    data_scope: str = "train"
    error: Optional[str] = None
    _log_path: Path = field(default=None, repr=False)  # type: ignore[assignment]
    _log_header_written: bool = field(default=False, repr=False)

    # ---------------- 训练循环调用
    def log_epoch(
        self,
        epoch: int,
        loss: Optional[float] = None,
        seconds: Optional[float] = None,
        n_eval: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """追加一行到 train_log.csv，并把本轮耗时记进 manifest.epoch_seconds。"""
        row = {"epoch": epoch}
        if loss is not None:
            row["loss"] = loss
        if seconds is not None:
            row["seconds"] = seconds
            self.epoch_seconds.append(float(seconds))
        if n_eval is not None:
            row["n_eval"] = n_eval
        row.update(extra)

        write_header = not self._log_path.exists()
        with open(self._log_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        self._log_header_written = True

    def set_best_epoch(self, epoch: int) -> None:
        self.best_epoch = int(epoch)

    def set_stop_reason(self, reason: str) -> None:
        """patience（耐心耗尽）/ max_epoch（最大轮数）/ failed（异常）/ completed。"""
        self.stop_reason = reason

    def set_data_scope(self, scope: str) -> None:
        """train（默认，只用训练集）/ full_history（仅原型演示版允许）。"""
        self.data_scope = scope

    def set_peak_memory(self, peak_mb: float) -> None:
        if self.gpu is None:
            self.gpu = {"name": "unknown"}
        self.gpu["peak_memory_mb"] = round(float(peak_mb), 1)

    def write_metrics(self, metrics: dict, filename: str = "metrics.json") -> Path:
        path = self.dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        return path

    # ---------------- manifest
    def _manifest(self) -> dict:
        return {
            "exp": self.exp,
            "model": self.model,
            "seed": self.seed,
            "git_commit": self.git_commit,
            "git_dirty": self.git_dirty,
            "git_dirty_files": self.git_dirty_files,
            "git_tags": self.git_tags,
            "command": self.command,
            "started_at": self.started_at,
            "ended_at": _now_iso(),
            "gpu": self.gpu,
            "epoch_seconds": self.epoch_seconds,
            "best_epoch": self.best_epoch,
            "stop_reason": self.stop_reason,
            "data_scope": self.data_scope,
            "error": self.error,
        }

    def write_manifest(self, extra: Optional[dict] = None) -> Path:
        manifest = self._manifest()
        if extra:
            manifest.update(extra)
        path = self.dir / "manifest.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        return path


# --------------------------------------------------------------------------- 工具
def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _command_line() -> str:
    return " ".join([Path(sys.argv[0]).name, *sys.argv[1:]]) if sys.argv else ""


# --------------------------------------------------------------------------- 主入口
_ACTIVE: list[RunHandle] = []


@contextmanager
def start_run(
    exp: str,
    model: str,
    seed: int,
    config: dict,
    results_dir: Optional[Path] = None,
):
    """创建运行目录并在退出时写 manifest.json。

    results_dir 仅供测试注入；正常调用使用模块级 RESULTS_DIR。
    """
    base = Path(results_dir) if results_dir is not None else RESULTS_DIR
    dirty, dirty_files = _is_git_dirty()

    exp_dir = f"_dirty_{exp}" if dirty else exp
    run_dir = base / exp_dir / model / f"seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    if dirty:
        print(
            f"\n{'=' * 72}\n"
            f"⚠️  工作区有 {len(dirty_files)} 个未提交改动，正式实验不应在此状态启动。\n"
            f"   结果已写入 {run_dir}（前缀 _dirty_），不会被 make_tables 采集。\n"
            f"   改动文件：{', '.join(dirty_files[:10])}"
            f"{' …' if len(dirty_files) > 10 else ''}\n"
            f"{'=' * 72}\n",
            file=sys.stderr,
        )

    handle = RunHandle(
        dir=run_dir,
        exp=exp,
        model=model,
        seed=seed,
        config=config,
        git_commit=_git_commit(),
        git_dirty=dirty,
        git_dirty_files=dirty_files,
        git_tags=_git_tags(),
        command=_command_line(),
        started_at=_now_iso(),
        gpu=_gpu_info(),
        _log_path=run_dir / "train_log.csv",
    )

    with open(run_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    _ACTIVE.append(handle)
    try:
        yield handle
    except BaseException as exc:  # 异常也要落 manifest，便于事后排查
        handle.stop_reason = "failed"
        handle.error = f"{type(exc).__name__}: {exc}"
        handle.write_manifest()
        raise
    else:
        handle.write_manifest()
    finally:
        if _ACTIVE and _ACTIVE[-1] is handle:
            _ACTIVE.pop()


def current_run() -> Optional[RunHandle]:
    return _ACTIVE[-1] if _ACTIVE else None