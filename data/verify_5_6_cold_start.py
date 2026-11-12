#!/usr/bin/env python3
"""
论文 5.6 节冷启动分层数据核算脚本
==================================
重跑实验后，用本脚本产出表5-8 的分层占比；表5-9 的分层 Recall 与表5-10 的
各路召回命中率需模型输出后另行填充，本脚本负责给出「占比」这一半的权威数值。

口径：
    以 train.csv 的 (user_id, item_id) 唯一对统计每用户训练集交互数。
    5-core 保证全量交互≥5 条，但 LOO 会切走最后两条（test+val），
    因此全量 5~6 条的用户在训练集中只剩 3~4 条，落入 0~4 条的超冷启动区间——
    这是训练集口径与全量口径的固有差异，不是数据错误。

用法：
    python data/verify_5_6_cold_start.py             # 默认 IS
    python data/verify_5_6_cold_start.py IS TH OP AJ # 多数据集
    python data/verify_5_6_cold_start.py IS --json   # 输出 JSON，便于回填论文

与相邻脚本的分工：
    prepare_data.py         产出 train/val/test，本脚本只读
    verify_4_1_data.py      核验 4.1 节（规模/长尾/λ）
    本脚本                   核验 5.6 节（冷启动分层），两者互不重叠
"""

import argparse
import json
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = SCRIPT_DIR / "processed"

# 表5-8 的分层阈值；上界取 10**9 表示无上界
LAYERS = [
    (0, 4, "超冷启动 UC", "新注册用户，近期首次浏览，无有效历史"),
    (5, 9, "冷启动 CS", "初期活跃用户，历史稀少，协同过滤信号弱"),
    (10, 29, "普通 NU", "中等活跃用户，具备基本协同过滤数据"),
    (30, 10**9, "重度 HU", "高活跃用户，交互丰富，协同过滤效果最佳"),
]


def load_train_pairs(name: str) -> pd.DataFrame:
    """
    读取 train 并去重到 (user_id, item_id)。

    AJ 同一对有多条行为记录，不去重会把行为条数当成交互数，
    使该用户被高估到更高的活跃层。
    """
    train = pd.read_csv(PROCESSED_DIR / name / "train.csv",
                        usecols=["user_id", "item_id"])
    return train.drop_duplicates(["user_id", "item_id"])


def layer_table(pairs: pd.DataFrame) -> pd.DataFrame:
    """
    生成 5.6.1 的分层统计表。

    返回列：用户层次 / 交互数范围 / 用户数 / 占比 / 该层人均训练交互 / 代表场景。
    占比分母为训练集中出现过的用户数（与表5-8「IS数据集占比」列口径一致）。
    """
    deg = pairs["user_id"].value_counts()
    n_users = len(deg)

    rows = []
    for lo, hi, label, scene in LAYERS:
        mask = (deg >= lo) & (deg <= hi)
        k = int(mask.sum())
        rows.append({
            "用户层次": label,
            "交互数范围": f"{lo}~{hi}" if hi < 10**9 else f"≥{lo}",
            "用户数": k,
            "占比": k / n_users,
            "该层人均训练交互": float(deg[mask].mean()) if k else 0.0,
            "代表场景": scene,
        })
    return pd.DataFrame(rows)


def recall_denominator(name: str) -> dict:
    """
    给出表5-9 的评价口径说明：测试集每用户一条正样本，分层 Recall 的分母。

    仅统计测试用户在各层的人数，用于校验表5-9 各行是否覆盖了全部测试用户。
    """
    test = pd.read_csv(PROCESSED_DIR / name / "test.csv",
                       usecols=["user_id", "item_id"])
    return {
        "测试用户数": int(test["user_id"].nunique()),
        "测试样例行数": len(test),
        "说明": "LOO 下每用户 1 条测试正样本，分层 Recall 分母为该层用户数",
    }


def run(name: str, as_json: bool) -> None:
    """核算单个数据集并打印（或输出 JSON）。"""
    pairs = load_train_pairs(name)
    table = layer_table(pairs)

    if as_json:
        payload = {
            "dataset": name,
            "train_users": int(len(pairs["user_id"].unique())),
            "train_pairs": int(len(pairs)),
            "avg_train_pairs_per_user": round(len(pairs) / pairs["user_id"].nunique(), 2),
            "layers": [
                {"layer": r["用户层次"], "range": r["交互数范围"],
                 "users": int(r["用户数"]), "share": round(float(r["占比"]), 4),
                 "avg_train_pairs": round(float(r["该层人均训练交互"]), 2)}
                for _, r in table.iterrows()
            ],
            "test": recall_denominator(name),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    n_users = pairs["user_id"].nunique()
    print(f"\n{'=' * 78}")
    print(f"{name}：训练集用户 {n_users:,}，训练集交互对 {len(pairs):,}，"
          f"人均 {len(pairs) / n_users:.1f} 条")
    print("=" * 78)
    show = table.copy()
    show["占比"] = show["占比"].map(lambda x: f"{x:.1%}")
    show["该层人均训练交互"] = show["该层人均训练交互"].map(lambda x: f"{x:.1f}")
    print(show.to_string(index=False))

    print(f"\n测试集口径：")
    for k, v in recall_denominator(name).items():
        print(f"  {k}：{v}")


def main() -> None:
    ap = argparse.ArgumentParser(description="论文 5.6 节冷启动分层核算")
    ap.add_argument("datasets", nargs="*", default=["IS"],
                    help="数据集短名，默认 IS")
    ap.add_argument("--json", action="store_true",
                    help="以 JSON 输出，便于回填论文表格")
    args = ap.parse_args()
    for name in args.datasets:
        run(name, args.json)


if __name__ == "__main__":
    main()
