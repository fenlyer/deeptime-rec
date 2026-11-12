"""
重跑后用于替换 5.6 冷启动分层数据的一次性核算脚本。

口径：
    按 train.csv 的 (user_id, item_id) 唯一对统计每用户训练集交互数，
    与论文 5.6.1「训练集口径而非用户全量交互」的说明一致；
    分层阈值沿用表5-8（0~4 / 5~9 / 10~29 / ≥30）。

用法：
    python data/verify_cold_start.py            # 默认 IS
    python data/verify_cold_start.py TH OP AJ   # 多数据集

输出可直接对照表5-8；表5-9 的 Recall 需要模型跑通后另行填充。
"""

import sys
from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parent / "processed"

# 表5-8 的分层阈值：(下界, 上界, 标签)，上界含闭区间
LAYERS = [(0, 4, "超冷启动 UC"), (5, 9, "冷启动 CS"),
          (10, 29, "普通 NU"), (30, 10**9, "重度 HU")]


def layer_stats(name: str) -> pd.DataFrame:
    """
    统计单个数据集的训练集用户分层。

    返回 DataFrame，列含用户数、占比、人均训练交互数；
    以 (user_id, item_id) 去重，防止 AJ 多行为记录重复计入用户度。
    """
    train = pd.read_csv(PROCESSED / name / "train.csv",
                        usecols=["user_id", "item_id"])
    pairs = train.drop_duplicates(["user_id", "item_id"])
    deg = pairs["user_id"].value_counts()
    n_users = len(deg)

    rows = []
    for lo, hi, label in LAYERS:
        mask = (deg >= lo) & (deg <= hi)
        k = int(mask.sum())
        rows.append({
            "数据集": name,
            "用户层次": label,
            "交互数范围": f"{lo}~{hi}" if hi < 10**9 else f"≥{lo}",
            "用户数": k,
            "占比": f"{k / n_users:.1%}",
            "该层人均训练交互": f"{deg[mask].mean():.1f}" if k else "—",
        })

    summary = pd.DataFrame(rows)
    print(f"\n{'=' * 62}\n{name}：训练集用户数 {n_users:,}，"
          f"人均训练交互 {len(pairs) / n_users:.1f}\n{'=' * 62}")
    print(summary.to_string(index=False))
    return summary


if __name__ == "__main__":
    targets = sys.argv[1:] or ["IS"]
    for t in targets:
        layer_stats(t)
