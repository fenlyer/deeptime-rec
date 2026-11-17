"""评估指标（S1-a）

给定每个用户测试物品的排名（rank）与可选的评分（rating），
计算 Recall@K（LOO 下等于 HR@K）与 NDCG@K。

口径
----
    - LOO 下每用户恰好 1 个测试正样本，IDCG@K = 1
    - 输入：{user_id: rank}，可选 {user_id: rating}
    - target 口径：
        ratings=None  → 全部用户
        ratings=dict  → 只评 rating >= threshold 的用户（由调用方过滤后传入）
    - 并列分数取悲观排名（与测试物品同分的都算排在前面），
      已在 eval/full_rank.py 的 rank 列中处理

公式
----
    Recall@K = (1/N) · Σᵤ 𝟙(rank_u ≤ K)

    NDCG@K = (1/N) · Σᵤ  𝟙(rank_u ≤ K) / log₂(rank_u + 1)
             （LOO 下 IDCG=1，分子即 DCG）
"""

from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np


def recall_at_k(
    ranks: Dict[str, float],
    k: int,
    ratings: Optional[Dict[str, float]] = None,
    threshold: float = 4.0,
) -> float:
    """Recall@K = 命中用户数 / 评价用户数。

    参数
    ----
    ranks : {user_id: rank} 每个用户的测试物品排名
    k     : 截断位置
    ratings : {user_id: rating} 可选；为 None 时评全部用户
    threshold : 只在 ratings 不为 None 时生效，过滤 rating < threshold 的用户
    """
    if ratings is None:
        user_ids = list(ranks.keys())
    else:
        user_ids = [u for u in ranks if u in ratings and ratings[u] >= threshold]
    if not user_ids:
        return 0.0
    n = len(user_ids)
    hits = sum(1 for u in user_ids if ranks.get(u, float("inf")) <= k)
    return hits / n


def ndcg_at_k(
    ranks: Dict[str, float],
    k: int,
    ratings: Optional[Dict[str, float]] = None,
    threshold: float = 4.0,
) -> float:
    """NDCG@K（LOO 下 IDCG=1）。

    同 recall_at_k 的口径与参数。
    当 rank > K 时该用户的 DCG=0。
    """
    if ratings is None:
        user_ids = list(ranks.keys())
    else:
        user_ids = [u for u in ranks if u in ratings and ratings[u] >= threshold]
    if not user_ids:
        return 0.0
    n = len(user_ids)
    total = 0.0
    for u in user_ids:
        rank = ranks.get(u, float("inf"))
        if rank <= k:
            # LOO 下 IDCG=1；DCG = 1/log2(rank+1)
            total += 1.0 / math.log2(rank + 1)
    return total / n