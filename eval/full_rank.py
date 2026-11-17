"""全排序评估（S1-a）

输入打分函数 + 屏蔽集合，输出 per_user DataFrame。

口径
----
    - 对每个测试用户，对其余全部物品（扣除训练/验证集里的物品）打分
    - 并列分数取悲观排名（与测试物品同分的物品都算排在它前面）
    - 输出列：user_id, test_item, rank, test_item_in_train, test_rating
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def full_rank(
    scores: pd.DataFrame,
    all_items: List[str],
    shielded: Set[Tuple[str, str]],
    test_df: pd.DataFrame,
    tie: str = "pessimistic",
) -> pd.DataFrame:
    """对每个测试用户做全排序，返回每用户一行。

    参数
    ----
    scores : DataFrame，列 user_id / item_id / score
             包含每个用户对所有候选物品的打分（含屏蔽物品，本函数内过滤）
    all_items : 全部物品 ID 列表
    shielded : {(user_id, item_id), ...} 训练+验证集的 (user, item) 对，评估时屏蔽
    test_df : 测试集 DataFrame，列 user_id / item_id / rating
    tie : 并列排名策略
          "pessimistic" — 同分都算排在前面（默认）
          "optimistic"  — 同分都算排在后面
          "average"     — 取平均排名

    返回
    ----
    DataFrame，列 user_id / test_item / rank / test_item_in_train / test_rating
    每用户一行，rank 为该用户测试物品在屏蔽后候选中的排名。
    """
    rows = []
    for _, test_row in test_df.iterrows():
        uid = str(test_row["user_id"])
        test_item = str(test_row["item_id"])
        test_rating = test_row.get("rating", None)

        # 该用户在屏蔽集中的物品
        user_shielded = {it for (u, it) in shielded if u == uid}
        # 该用户的候选物品 = 全部 - 屏蔽
        candidates = [it for it in all_items if it not in user_shielded]

        # 该用户对各候选物品的打分
        user_scores = scores[(scores["user_id"] == uid) & (scores["item_id"].isin(candidates))]
        if user_scores.empty:
            rows.append({
                "user_id": uid,
                "test_item": test_item,
                "rank": len(candidates) + 1,  # 未打分 → 排在最后
                "test_item_in_train": test_item in user_shielded,
                "test_rating": test_rating,
            })
            continue

        # 测试物品的分数
        test_score_row = user_scores[user_scores["item_id"] == test_item]
        if test_score_row.empty:
            # 测试物品不在候选中（被屏蔽或无打分）
            rows.append({
                "user_id": uid,
                "test_item": test_item,
                "rank": len(candidates) + 1,
                "test_item_in_train": test_item in user_shielded,
                "test_rating": test_rating,
            })
            continue

        test_score = float(test_score_row["score"].iloc[0])

        # 计算排名
        other_scores = user_scores[user_scores["item_id"] != test_item]["score"].to_numpy(dtype=np.float64)
        rank = _compute_rank(test_score, other_scores, tie)

        rows.append({
            "user_id": uid,
            "test_item": test_item,
            "rank": rank,
            "test_item_in_train": test_item in user_shielded,
            "test_rating": test_rating,
        })

    return pd.DataFrame(rows)


def _compute_rank(test_score: float, other_scores: np.ndarray, tie: str) -> float:
    """计算测试物品的排名。

    排名定义：测试物品在全部候选（含自身）中的位置。
    - pessimistic: rank = 1 + (比它大的个数) + (与它同分的个数)
                   （同分物品都算排在前面，rank 最保守）
    - optimistic:  rank = 1 + (比它大的个数)
                   （同分物品都算排在后面，rank 最乐观）
    - average:     rank = 1 + (比它大的个数) + 0.5 * (与它同分的个数)
                   （取平均排名）
    """
    n_better = int((other_scores > test_score).sum())
    n_equal = int((other_scores == test_score).sum())

    if tie == "optimistic":
        return 1 + n_better
    elif tie == "pessimistic":
        return 1 + n_better + n_equal
    elif tie == "average":
        return 1 + n_better + 0.5 * n_equal
    else:
        raise ValueError(f"未知排名策略：{tie}，可选 pessimistic/optimistic/average")


def run_full_rank(
    scores_path: Path,
    train_path: Path,
    val_path: Path,
    test_path: Path,
    cfg_path: Path,
    out_path: Path,
) -> None:
    """CLI 入口：从 parquet 文件做全排序评估，输出 per_user.parquet。"""
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    scores = pd.read_parquet(scores_path)
    train = pd.read_parquet(train_path)
    val = pd.read_parquet(val_path)
    test = pd.read_parquet(test_path)

    all_items = sorted(
        pd.concat([train["item_id"], val["item_id"], test["item_id"]]).unique().tolist()
    )
    shielded = set(
        (str(r["user_id"]), str(r["item_id"]))
        for _, r in pd.concat([train[["user_id", "item_id"]], val[["user_id", "item_id"]]]).iterrows()
    )

    tie = cfg.get("rank_tie", "pessimistic")
    target = cfg.get("target", "all")
    pos_threshold = cfg.get("pos_threshold", 4)

    if target == "pos":
        eval_test = test[test["rating"] >= pos_threshold].copy()
    else:
        eval_test = test.copy()

    out = full_rank(
        scores=scores,
        all_items=all_items,
        shielded=shielded,
        test_df=eval_test,
        tie=tie,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_path, index=False)
    print(f"→ {out_path.relative_to(REPO_ROOT)}  ({len(out)} 行)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="全排序评估")
    ap.add_argument("--scores", type=Path, required=True, help="打分 parquet 路径")
    ap.add_argument("--train", type=Path, required=True, help="训练集 parquet 路径")
    ap.add_argument("--val", type=Path, required=True, help="验证集 parquet 路径")
    ap.add_argument("--test", type=Path, required=True, help="测试集 parquet 路径")
    ap.add_argument("--config", type=Path, required=True, help="eval.yaml 路径")
    ap.add_argument("--output", type=Path, required=True, help="输出 per_user.parquet 路径")
    args = ap.parse_args()
    run_full_rank(
        scores_path=args.scores,
        train_path=args.train,
        val_path=args.val,
        test_path=args.test,
        cfg_path=args.config,
        out_path=args.output,
    )