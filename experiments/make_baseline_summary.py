"""召回基线汇总（S-recall-base）

读 results/ch3_recall/baselines/{model}/seed{n}/metrics.json → summary.csv。

口径
----
    - 均值/标准差跨 seed 计算（ddof=1），不做任何取整。
    - 只收 eval/ 口径的指标（Recall@K / NDCG@K）；recbole_ 前缀字段是对账用的，
      不进 summary，避免与论文数字混在一起。
    - 跳过 manifest.git_dirty 的 run 与 "_" 开头的目录。
    - summary.csv 是给人看的检查表；论文数字仍以 make_tables → numbers.json 为准。

用法
----
    python experiments/make_baseline_summary.py
    python experiments/make_baseline_summary.py --baselines-dir results/ch3_recall/baselines
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "experiments"))

from run_recall_baseline import collect_summary_rows  # noqa: E402

DEFAULT_DIR = REPO_ROOT / "results" / "ch3_recall" / "baselines"


def main() -> int:
    ap = argparse.ArgumentParser(description="召回基线 summary.csv")
    ap.add_argument("--baselines-dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--output", type=Path, default=None,
                    help="默认写到 {baselines-dir}/summary.csv")
    args = ap.parse_args()

    rows = collect_summary_rows(args.baselines_dir)
    out = args.output or (args.baselines_dir / "summary.csv")
    out.parent.mkdir(parents=True, exist_ok=True)

    fields = ["model", "metric", "mean", "std", "n_seeds"]
    with open(out, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r[k] is None else r[k]) for k in fields})

    runs = sorted(Path(args.baselines_dir).glob("*/seed*/metrics.json"))
    try:
        shown = out.resolve().relative_to(REPO_ROOT)
    except ValueError:  # 输出不在仓库内（测试/自定义目录）
        shown = out
    print(f"读入 {len(runs)} 个 run → {shown}  ({len(rows)} 行)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())