"""基线结果快照（R0 归档 / R3 验收用）

把 results/ch3_recall/baselines/ 下所有 run 的关键数字压成一份 CSV 快照，
用于重跑前后逐 seed 对照（验收 A1：重跑不得改变任何准确率数字）。

口径
----
    - 每个 seed 一行，字段：model, seed, 指标..., elapsed_s, best_epoch, git_commit
    - 指标取 metrics.json 里非 recbole_ 前缀的项（即 eval/ 重算口径，进论文的那套）
    - 不做任何聚合，原始值照抄，浮点用 repr 全精度写出

用法
----
    python experiments/snapshot_baselines.py                      # 默认读 baselines/，写 _archive/v1-20261127/summary.csv
    python experiments/snapshot_baselines.py --runs-dir R --output O
    python experiments/snapshot_baselines.py --compare A.csv B.csv  # 逐 seed 比对两份快照
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_RUNS = REPO_ROOT / "results" / "ch3_recall" / "baselines"
DEFAULT_OUT = REPO_ROOT / "results" / "ch3_recall" / "_archive" / "v1-20261127" / "summary.csv"

# 进论文的指标（与 experiments/make_baseline_summary.py 同口径：排除 recbole_ 前缀）
METRICS = ["Recall@10", "Recall@20", "NDCG@10", "NDCG@20"]


def collect(runs_dir: Path) -> list[dict]:
    """扫描 {runs_dir}/{model}/seed{n}/，返回逐 seed 行列表。"""
    rows: list[dict] = []
    if not runs_dir.is_dir():
        return rows
    for model_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        for seed_dir in sorted(model_dir.glob("seed*")):
            metrics_path = seed_dir / "metrics.json"
            if not metrics_path.exists():
                continue
            metrics = json.loads(metrics_path.read_text(encoding="utf8"))
            row: dict = {"model": model_dir.name, "seed": seed_dir.name[4:]}
            for m in METRICS:
                row[m] = repr(metrics.get(m)) if m in metrics else ""
            manifest_path = seed_dir / "manifest.json"
            if manifest_path.exists():
                mf = json.loads(manifest_path.read_text(encoding="utf8"))
                row["elapsed_s"] = mf.get("elapsed_s", "")
                row["best_epoch"] = mf.get("best_epoch", "")
                row["git_commit"] = (mf.get("git_commit") or "")[:7]
            rows.append(row)
    return rows


def write(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["model", "seed", *METRICS, "elapsed_s", "best_epoch", "git_commit"]
    with open(output, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load(path: Path) -> dict[tuple[str, str], dict]:
    with open(path, newline="", encoding="utf8") as f:
        return {(r["model"], r["seed"]): r for r in csv.DictReader(f)}


def compare(a_path: Path, b_path: Path, rel_tol: float = 1e-9) -> int:
    """逐 (model, seed) 比对 METRICS。返回退出码：0 一致，1 有差异。"""
    a, b = load(a_path), load(b_path)
    keys = sorted(set(a) | set(b))
    diffs: list[str] = []
    for k in keys:
        ra, rb = a.get(k), b.get(k)
        if ra is None or rb is None:
            diffs.append(f"{k[0]}/seed{k[1]}: 只在一侧存在")
            continue
        for m in METRICS:
            va, vb = ra.get(m, ""), rb.get(m, "")
            if va == vb:
                continue
            try:
                fa, fb = float(va), float(vb)
            except (TypeError, ValueError):
                diffs.append(f"{k[0]}/seed{k[1]} {m}: 非数值 {va!r} vs {vb!r}")
                continue
            scale = max(abs(fa), abs(fb), 1e-12)
            if abs(fa - fb) / scale > rel_tol:
                diffs.append(f"{k[0]}/seed{k[1]} {m}: {va} vs {vb}")
    print(f"比对 {a_path.name} ↔ {b_path.name}：{len(keys)} 个 run")
    if diffs:
        print(f"❌ {len(diffs)} 处差异（rel_tol={rel_tol}）：")
        for d in diffs[:20]:
            print("   " + d)
        return 1
    print(f"✅ 全部一致（4 个指标 × {len(keys)} 个 run）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="基线结果快照 / 重跑前后比对")
    ap.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--compare", nargs=2, type=Path, metavar=("A", "B"))
    ap.add_argument("--rel-tol", type=float, default=1e-9)
    args = ap.parse_args()

    if args.compare:
        return compare(args.compare[0], args.compare[1], args.rel_tol)

    rows = collect(args.runs_dir)
    write(rows, args.output)
    print(f"✅ {len(rows)} 个 run → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())