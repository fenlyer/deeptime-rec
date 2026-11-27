"""S1-c 运行记录测试：common/run.py

覆盖：
    - 目录命名：clean → results/{exp}/{model}/seed{n}/；dirty → results/_dirty_{exp}/...
    - manifest.json 字段齐全，取值来自真实 git 状态而非硬编码
    - 工作区有未提交改动时 manifest.git_dirty 为 True 且目录落到 _dirty_ 前缀
    - train_log.csv 逐轮追加、epoch_seconds 与 best_epoch 写入 manifest
    - config.yaml 落盘内容与传入 config 一致
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "common"))

import run as run_mod  # noqa: E402


# --------------------------------------------------------------------------- 目录命名
def test_clean_run_dir_has_no_dirty_prefix(tmp_path, monkeypatch):
    """工作区干净时目录为 results/{exp}/{model}/seed{n}/。"""
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (False, []))
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    with run_mod.start_run("smoke", "lightgcn", 0, {"lr": 0.001}) as h:
        out_dir = h.dir

    assert out_dir == tmp_path / "smoke" / "lightgcn" / "seed0"
    assert out_dir.is_dir()


def test_dirty_run_dir_gets_dirty_prefix(tmp_path, monkeypatch):
    """工作区不干净时目录前缀改为 _dirty_{exp}。"""
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (True, ["eval/full_rank.py"]))
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    with run_mod.start_run("recall_main", "bpr", 2, {"lr": 0.01}) as h:
        out_dir = h.dir

    assert out_dir == tmp_path / "_dirty_recall_main" / "bpr" / "seed2"
    assert out_dir.is_dir()


def test_dirty_run_warns_loudly(tmp_path, monkeypatch, capsys):
    """dirty 时必须打印醒目警告，不能静默写结果。"""
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (True, ["a.py"]))
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    with run_mod.start_run("smoke", "m", 0, {}):
        pass

    err = capsys.readouterr().err
    assert "未提交" in err or "dirty" in err.lower()
    assert "a.py" in err


def test_untracked_source_file_counts_as_dirty(monkeypatch):
    """未跟踪的源码文件算 dirty —— 红线：脏工作区不启动正式实验。"""
    monkeypatch.setattr(
        run_mod, "_git",
        lambda args: " M eval/metrics.py\n?? eval/new_module.py" if "status" in args else None,
    )
    dirty, files = run_mod._is_git_dirty()
    assert dirty is True
    assert "eval/new_module.py" in files
    assert "eval/metrics.py" in files


def test_untracked_output_files_do_not_count_as_dirty(monkeypatch):
    """结果/产物目录下的新文件不算 dirty，否则每次运行都判脏。"""
    monkeypatch.setattr(
        run_mod, "_git",
        lambda args: "?? results/recall_main/x/seed0/metrics.json" if "status" in args else None,
    )
    dirty, files = run_mod._is_git_dirty()
    assert dirty is False
    assert files == []


def test_clean_tree_reports_not_dirty(monkeypatch):
    monkeypatch.setattr(run_mod, "_git", lambda args: "" if "status" in args else None)
    dirty, files = run_mod._is_git_dirty()
    assert dirty is False
    assert files == []


# --------------------------------------------------------------------------- manifest 字段
def test_manifest_has_all_required_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (False, []))
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    with run_mod.start_run("smoke", "m", 0, {"lr": 1e-3}) as h:
        h.set_best_epoch(7)
        h.set_stop_reason("patience")

    manifest = json.loads((h.dir / "manifest.json").read_text(encoding="utf-8"))
    for key in (
        "git_commit", "git_dirty", "git_dirty_files", "git_tags", "command",
        "started_at", "ended_at", "gpu", "epoch_seconds", "best_epoch", "stop_reason",
        "exp", "model", "seed", "data_scope",
    ):
        assert key in manifest, f"manifest 缺字段 {key}"

    assert manifest["exp"] == "smoke"
    assert manifest["model"] == "m"
    assert manifest["seed"] == 0
    assert manifest["git_dirty"] is False
    assert manifest["best_epoch"] == 7
    assert manifest["stop_reason"] == "patience"


def test_manifest_git_commit_is_real_sha():
    """git_commit 必须是真的 40 位 sha，而不是占位符。"""
    commit = run_mod._git_commit()
    if commit is None:
        pytest.skip("不在 git 仓库内")
    assert len(commit) == 40
    assert all(c in "0123456789abcdef" for c in commit)


def test_manifest_records_all_head_tags(tmp_path, monkeypatch):
    """data_tag 口径：HEAD 上全部 tag（可为空列表）。"""
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (False, []))
    monkeypatch.setattr(run_mod, "_git_tags", lambda: ["data-v1", "recall-freeze"])
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    with run_mod.start_run("smoke", "m", 0, {}) as h:
        pass

    manifest = json.loads((h.dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["git_tags"] == ["data-v1", "recall-freeze"]


# --------------------------------------------------------------------------- train_log
def test_epoch_logging_appends_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (False, []))
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    with run_mod.start_run("smoke", "m", 0, {}) as h:
        h.log_epoch(epoch=1, loss=1.5, seconds=0.3, n_eval=0.41)
        h.log_epoch(epoch=2, loss=1.2, seconds=0.28, n_eval=0.45)
        h.log_epoch(epoch=3, loss=1.1, seconds=0.31, n_eval=0.44)

    log = (h.dir / "train_log.csv").read_text(encoding="utf-8").strip().splitlines()
    assert log[0].startswith("epoch,"), "train_log.csv 缺表头"
    assert len(log) == 4  # 表头 + 3 轮

    manifest = json.loads((h.dir / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["epoch_seconds"]) == 3
    assert manifest["epoch_seconds"] == pytest.approx([0.3, 0.28, 0.31])


def test_epoch_seconds_empty_when_no_logging(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (False, []))
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    with run_mod.start_run("smoke", "m", 0, {}) as h:
        pass

    manifest = json.loads((h.dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["epoch_seconds"] == []


# --------------------------------------------------------------------------- config
def test_config_written_as_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (False, []))
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    cfg = {"lr": 0.001, "weight_decay": 1e-4, "epochs": 50, "target": "all"}
    with run_mod.start_run("smoke", "m", 0, cfg) as h:
        pass

    written = yaml.safe_load((h.dir / "config.yaml").read_text(encoding="utf-8"))
    assert written == cfg


# --------------------------------------------------------------------------- 时间戳
def test_manifest_timestamps_are_iso_with_timezone(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (False, []))
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    with run_mod.start_run("smoke", "m", 0, {}) as h:
        pass

    manifest = json.loads((h.dir / "manifest.json").read_text(encoding="utf-8"))
    from datetime import datetime
    for key in ("started_at", "ended_at"):
        dt = datetime.fromisoformat(manifest[key])
        assert dt.tzinfo is not None, f"{key} 缺时区"
    assert manifest["ended_at"] >= manifest["started_at"]


# --------------------------------------------------------------------------- manifest extra
def test_write_manifest_extra_survives_context_exit(tmp_path, monkeypatch):
    """write_manifest(extra=...) 的字段在 contextmanager 退出时不能被抹掉。

    历史 bug：退出时 start_run 再写一次 manifest，把 extra 覆盖成只剩固定字段。
    """
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (False, []))
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    with run_mod.start_run("smoke", "m", 0, {}) as h:
        h.write_manifest(extra={"elapsed_s": 12.3, "recbole_metrics": {"x": 1}})

    manifest = json.loads((h.dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["elapsed_s"] == pytest.approx(12.3)
    assert manifest["recbole_metrics"] == {"x": 1}
    assert manifest["exp"] == "smoke"  # 固定字段仍在


# --------------------------------------------------------------------------- 异常路径
def test_exception_still_writes_manifest(tmp_path, monkeypatch):
    """训练中途抛异常时也要落 manifest，标记 stop_reason=failed。"""
    monkeypatch.setattr(run_mod, "_is_git_dirty", lambda: (False, []))
    monkeypatch.setattr(run_mod, "RESULTS_DIR", tmp_path)

    with pytest.raises(RuntimeError):
        with run_mod.start_run("smoke", "m", 0, {}) as h:
            raise RuntimeError("训练崩了")

    manifest = json.loads((h.dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["stop_reason"] == "failed"
    assert "训练崩了" in manifest.get("error", "")