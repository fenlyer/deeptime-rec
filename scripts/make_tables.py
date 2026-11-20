"""数字管线：results/ → thesis/generated/numbers.json（S1-d）

CLAUDE.md 红线 2 的唯一实现：论文中的实验数字只能来自这里，正文用 {{n:key}} 引用。

口径
----
    - 只聚合 seed 维度：均值/标准差跨 seed 计算（ddof=1），不做任何取整。
    - 用户级统计（配对检验、分层）由 eval/ 产出后作为独立 JSON 读入，本脚本不重算。
    - 跳过以 "_" 开头的目录（results/_smoke/ 等冒烟产物）与 git_dirty 的 run。
    - 缺失指标不产生 key（而不是产生值为 null 的 key），这样正文引用时会直接构建失败。
    - 输出按键名排序，两次运行字节一致（无时间戳）。

key 命名
--------
    recall.{model}.{metric}.mean|std|seeds     召回指标
    rank.{model}.{metric}.mean|std|seeds       排序指标
    strata.{model}.{layer}.{metric}            分层指标（读 eval/strata 的 JSON）
    sig.{a}_vs_{b}.{stat}                      配对检验（读 eval/paired_test 的 JSON）
    profile.{ds}.{field}                       数据画像
    sys.{item}.{stat}                          系统评测

用法
----
    python scripts/make_tables.py                    # results/ → thesis/generated/
    python scripts/make_tables.py --results-dir R --output O
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS = REPO_ROOT / "results"
DEFAULT_OUTPUT = REPO_ROOT / "thesis" / "generated" / "numbers.json"

# 实验目录 → key 前缀。未列出的目录按目录名推断。
EXP_PREFIX = {
    "ch3_recall": "recall",
    "ch4_rank": "rank",
}


# --------------------------------------------------------------------------- 工具
def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _seed_dirs(model_dir: Path) -> list[tuple[int, Path]]:
    """返回 [(seed, dir)]，按 seed 数值升序。"""
    out: list[tuple[int, Path]] = []
    for d in model_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("seed"):
            continue
        try:
            out.append((int(d.name[4:]), d))
        except ValueError:
            continue
    return sorted(out)


def _is_dirty(seed_dir: Path) -> bool:
    """manifest.json 标记 git_dirty 的 run 不进正式数字。"""
    mf = seed_dir / "manifest.json"
    if not mf.exists():
        return False
    try:
        return bool(json.loads(mf.read_text(encoding="utf8")).get("git_dirty"))
    except (json.JSONDecodeError, OSError):
        return False


def _rel(path: Path, root: Path) -> str:
    """相对 root 的 posix 路径，作为 source 字段。"""
    return path.relative_to(root).as_posix()


def _load_metrics(seed_dir: Path) -> dict:
    p = seed_dir / "metrics.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


# --------------------------------------------------------------------------- 聚合
def _aggregate_experiment(
    exp_dir: Path, prefix: str, root: Path, nums: dict[str, dict]
) -> None:
    """遍历 {exp}/{model}/seed{n}/metrics.json，写入 mean/std/seeds。"""
    for model_dir in sorted(p for p in exp_dir.iterdir() if p.is_dir()):
        model = model_dir.name
        if model.startswith("_"):
            continue

        per_metric: dict[str, list[tuple[float, str]]] = {}
        for seed, seed_dir in _seed_dirs(model_dir):
            if _is_dirty(seed_dir):
                continue
            metrics = _load_metrics(seed_dir)
            src = _rel(seed_dir / "metrics.json", root)
            for name, value in metrics.items():
                if not _is_number(value):
                    continue
                per_metric.setdefault(name, []).append((float(value), src))

        for metric in sorted(per_metric):
            pairs = per_metric[metric]
            values = [v for v, _ in pairs]
            # source 指向第一个 seed 的 metrics.json；逐 seed 值本身在 seeds 里
            src = pairs[0][1]
            base = f"{prefix}.{model}.{metric}"

            nums[f"{base}.mean"] = {
                "value": statistics.fmean(values),
                "source": src,
                "n_seeds": len(values),
            }
            nums[f"{base}.std"] = {
                "value": statistics.stdev(values) if len(values) > 1 else None,
                "source": src,
                "n_seeds": len(values),
            }
            nums[f"{base}.seeds"] = {
                "value": values,
                "source": src,
                "n_seeds": len(values),
            }


def _collect_json_dir(
    path: Path, prefix: str, root: Path, nums: dict[str, dict]
) -> None:
    """把 results/<dir>/*.json 的标量字段展平成 {prefix}.{stem}.{field}。"""
    if not path.is_dir():
        return
    for f in sorted(path.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        _flatten(data, f"{prefix}.{f.stem}", _rel(f, root), nums)


def _flatten(data: dict, prefix: str, src: str, nums: dict[str, dict]) -> None:
    """递归展平嵌套 dict；只收标量（数值或 None）。"""
    for k, v in sorted(data.items()):
        key = f"{prefix}.{k}"
        if isinstance(v, dict):
            _flatten(v, key, src, nums)
        elif _is_number(v) or v is None:
            nums[key] = {"value": v, "source": src}


# --------------------------------------------------------------------------- 入口
def collect(results_dir: Path) -> dict[str, dict]:
    """扫描 results_dir，返回 {key: {value, source, ...}}，按键名排序。"""
    results_dir = Path(results_dir)
    nums: dict[str, dict] = {}
    if not results_dir.is_dir():
        return nums

    for exp_dir in sorted(p for p in results_dir.iterdir() if p.is_dir()):
        name = exp_dir.name
        if name.startswith("_"):
            continue

        if name in EXP_PREFIX:
            _aggregate_experiment(exp_dir, EXP_PREFIX[name], results_dir, nums)
        elif name == "strata":
            _collect_json_dir(exp_dir, "strata", results_dir, nums)
        elif name == "profile":
            _collect_json_dir(exp_dir, "profile", results_dir, nums)
        elif name == "sig":
            _collect_json_dir(exp_dir, "sig", results_dir, nums)
        elif name == "ch5_system":
            _collect_json_dir(exp_dir, "sys", results_dir, nums)
        else:
            _collect_json_dir(exp_dir, name, results_dir, nums)

    return dict(sorted(nums.items()))


def dumps(nums: dict[str, dict]) -> str:
    """稳定的 JSON 文本：键排序、缩进 2、保留原始精度、无时间戳。"""
    return json.dumps(nums, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write(nums: dict[str, dict], output: Path) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps(nums), encoding="utf8")


def main() -> int:
    ap = argparse.ArgumentParser(description="results/ → thesis/generated/numbers.json")
    ap.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()

    nums = collect(args.results_dir)
    write(nums, args.output)

    print(f"✅ {len(nums)} 个数字 → {args.output}")
    if not nums:
        print("   （results/ 下没有可聚合的 run，输出为空表）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
