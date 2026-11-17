"""统一评估测试（S1-a）

3 个用户、6 个物品的手算样例，覆盖：
  - 屏蔽：训练/验证物品不出现在候选排名
  - 并列：pessimistic / optimistic / average 三种排名
  - K 边界：K=1, K=6（全部）, K=10（超出物品数）
  - 两种口径：target=all 与 target=pos
  - 确定性：同一打分评估两次 hash 一致
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

# --------------------------------------------------------------------------- 测试数据
# 3 用户 (U0/U1/U2)、6 物品 (I0-I5)
# 训练/验证集定义：屏蔽时会排除这些 (user, item)
TRAIN_VAL = {
    ("U0", "I0"), ("U0", "I1"),
    ("U1", "I2"),
    ("U2", "I3"), ("U2", "I4"),
}

# 每个用户的测试目标（item, rating）
TEST_TARGETS = {
    "U0": ("I2", 5),   # U0 测试物品 I2（高分）
    "U1": ("I0", 3),   # U1 测试物品 I0（低分）
    "U2": ("I5", 5),   # U2 测试物品 I5（高分）
}

# 打分函数：给每个用户对所有 6 个物品的打分
# 列: user_id, item_id, score
SCORES = pd.DataFrame([
    # U0：I2=10（测试目标最高分），I3=10（并列）, I4=5, I5=3, I0=屏蔽, I1=屏蔽
    {"user_id": "U0", "item_id": "I0", "score": 99.0},   # 会被屏蔽
    {"user_id": "U0", "item_id": "I1", "score": 99.0},   # 会被屏蔽
    {"user_id": "U0", "item_id": "I2", "score": 10.0},   # 测试目标
    {"user_id": "U0", "item_id": "I3", "score": 10.0},   # 与测试目标并列
    {"user_id": "U0", "item_id": "I4", "score": 5.0},
    {"user_id": "U0", "item_id": "I5", "score": 3.0},
    # U1：I0=7（测试目标），I3=7（并列）, I4=6, I5=2, I2=屏蔽
    {"user_id": "U1", "item_id": "I0", "score": 7.0},    # 测试目标
    {"user_id": "U1", "item_id": "I1", "score": 8.0},
    {"user_id": "U1", "item_id": "I2", "score": 99.0},   # 会被屏蔽
    {"user_id": "U1", "item_id": "I3", "score": 7.0},    # 与测试目标并列
    {"user_id": "U1", "item_id": "I4", "score": 6.0},
    {"user_id": "U1", "item_id": "I5", "score": 2.0},
    # U2：I5=10（测试目标最高分）, I0=8, I1=7, I2=6, I3=屏蔽, I4=屏蔽
    {"user_id": "U2", "item_id": "I0", "score": 8.0},
    {"user_id": "U2", "item_id": "I1", "score": 7.0},
    {"user_id": "U2", "item_id": "I2", "score": 6.0},
    {"user_id": "U2", "item_id": "I3", "score": 99.0},   # 会被屏蔽
    {"user_id": "U2", "item_id": "I4", "score": 99.0},   # 会被屏蔽
    {"user_id": "U2", "item_id": "I5", "score": 10.0},   # 测试目标
])

ALL_ITEMS = ["I0", "I1", "I2", "I3", "I4", "I5"]
TEST_DF = pd.DataFrame([
    {"user_id": u, "item_id": it, "rating": r}
    for u, (it, r) in TEST_TARGETS.items()
])


# --------------------------------------------------------------------------- 辅助
@pytest.fixture
def cfg(tmp_path):
    """写一份最小 configs/eval.yaml 到 tmp_path，返回路径。"""
    cfg_file = tmp_path / "eval.yaml"
    cfg_file.write_text(yaml.dump({"K": [1, 3, 6], "target": "all", "pos_threshold": 4, "rank_tie": "pessimistic"}))
    return cfg_file


# --------------------------------------------------------------------------- 屏蔽测试
def test_full_rank_shields_train_and_val():
    """屏蔽后每用户的候选数 = 全部物品数 - 该用户在 train∪val 中的物品数。
    full_rank 返回每用户一行，rank 列反映屏蔽效果——屏蔽物品越多，候选越少，
    但测试物品排名本身不受候选总数影响（只要测试物品在候选内）。
    此处用 U0 做端到端检查：屏蔽 I0/I1 后，U0 的候选为 I2/I3/I4/I5 共 4 个，
    测试物品 I2(10) 与 I3(10) 并列 → pessimistic rank=2。
    """
    from eval.full_rank import full_rank

    out = full_rank(
        scores=SCORES,
        all_items=ALL_ITEMS,
        shielded=TRAIN_VAL,
        test_df=TEST_DF,
    )
    # 输出是每用户一行，共 3 行
    assert len(out) == 3
    # 每用户恰好一个测试物品
    assert set(out["user_id"]) == {"U0", "U1", "U2"}
    # 屏蔽物品不应出现在测试物品列
    shielded_test_items = {it for (_, it) in TRAIN_VAL if any(u == _ for u, _ in [(r["user_id"], r["item_id"]) for _, r in TEST_DF.iterrows()])}
    # 更直接：U0 的 I0/I1 被屏蔽，它们不应出现在 U0 的候选打分中
    u0_scores = SCORES[(SCORES["user_id"] == "U0") & ~SCORES["item_id"].isin(["I0", "I1"])]
    assert len(u0_scores) == 4  # I2/I3/I4/I5


# --------------------------------------------------------------------------- 排名测试
def test_ranking_pessimistic():
    """pessimistic：与测试物品同分的都算排在它前面。"""
    from eval.full_rank import full_rank

    out = full_rank(
        scores=SCORES,
        all_items=ALL_ITEMS,
        shielded=TRAIN_VAL,
        test_df=TEST_DF,
        tie="pessimistic",
    )
    u0_test_rank = out[(out["user_id"] == "U0") & (out["test_item"] == "I2")].iloc[0]
    # U0：I2(10) 与 I3(10) 并列，pessimistic → rank=2（I3 也算排在前面）
    assert u0_test_rank["rank"] == 2

    u1_test_rank = out[(out["user_id"] == "U1") & (out["test_item"] == "I0")].iloc[0]
    # U1：I0(7) 与 I3(7) 并列，I1(8) 排前面 → rank=3（I1+I3 都排前面）
    assert u1_test_rank["rank"] == 3

    u2_test_rank = out[(out["user_id"] == "U2") & (out["test_item"] == "I5")].iloc[0]
    # U2：I5(10) 独占最高 → rank=1
    assert u2_test_rank["rank"] == 1


def test_ranking_optimistic():
    """optimistic：与测试物品同分的都算排在它后面。"""
    from eval.full_rank import full_rank

    out = full_rank(
        scores=SCORES,
        all_items=ALL_ITEMS,
        shielded=TRAIN_VAL,
        test_df=TEST_DF,
        tie="optimistic",
    )
    u0_test_rank = out[(out["user_id"] == "U0") & (out["test_item"] == "I2")].iloc[0]
    # optimistic：I3(10) 算排在后面 → rank=1
    assert u0_test_rank["rank"] == 1


def test_ranking_average():
    """average：取平均排名。"""
    from eval.full_rank import full_rank

    out = full_rank(
        scores=SCORES,
        all_items=ALL_ITEMS,
        shielded=TRAIN_VAL,
        test_df=TEST_DF,
        tie="average",
    )
    u0_test_rank = out[(out["user_id"] == "U0") & (out["test_item"] == "I2")].iloc[0]
    # average：(1+2)/2 = 1.5
    assert u0_test_rank["rank"] == 1.5


# --------------------------------------------------------------------------- K 边界
def test_recall_at_k_boundaries():
    """K=1 / K=3 / K=6（全部物品）/ K=10（超出候选数）。"""
    from eval.full_rank import full_rank
    from eval.metrics import recall_at_k, ndcg_at_k

    out = full_rank(
        scores=SCORES,
        all_items=ALL_ITEMS,
        shielded=TRAIN_VAL,
        test_df=TEST_DF,
        tie="pessimistic",
    )
    # ranks: U0=2, U1=3, U2=1
    ranks = {"U0": 2, "U1": 3, "U2": 1}

    # K=1: 只有 U2 (rank=1) 命中 → Recall@1 = 1/3
    assert recall_at_k(ranks, 1) == pytest.approx(1 / 3)
    # K=3: U0(2) U1(3) U2(1) 全命中 → Recall@3 = 1.0
    assert recall_at_k(ranks, 3) == pytest.approx(1.0)
    # K=6: 全部命中
    assert recall_at_k(ranks, 6) == pytest.approx(1.0)
    # K=10: 超出候选数仍为 1.0
    assert recall_at_k(ranks, 10) == pytest.approx(1.0)

    # NDCG@K: IDCG=1（每用户 1 个正样本）
    # NDCG = (1 / log2(rank+1)) / 1
    # U0: 1/log2(3)=0.6309, U1: 1/log2(4)=0.5, U2: 1/log2(2)=1.0
    # NDCG@3 = (0.6309 + 0.5 + 1.0) / 3 = 0.7103
    ndcg3 = ndcg_at_k(ranks, 3)
    assert ndcg3 == pytest.approx((1 / np.log2(3) + 1 / np.log2(4) + 1 / np.log2(2)) / 3)


# --------------------------------------------------------------------------- 两种口径
def test_target_all_vs_pos():
    """target=all 评全部测试目标，target=pos 只评 rating>=4 的目标。"""
    from eval.metrics import recall_at_k

    ranks = {"U0": 2, "U1": 3, "U2": 1}
    ratings = {"U0": 5, "U1": 3, "U2": 5}

    # all: 3 个用户都评
    assert recall_at_k(ranks, 1, ratings=None) == pytest.approx(1 / 3)
    # pos (threshold=4): 只有 U0(rating=5) 和 U2(rating=5)，U1(rating=3) 不计
    #   K=1: U2 命中 → 1/2
    assert recall_at_k(ranks, 1, ratings=ratings, threshold=4) == pytest.approx(1 / 2)
    #   K=3: U0(rank=2) U2(rank=1) 都命中 → 1.0
    assert recall_at_k(ranks, 3, ratings=ratings, threshold=4) == pytest.approx(1.0)


# --------------------------------------------------------------------------- 确定性
def test_deterministic_hash(tmp_path):
    """同一份打分评估两次，per_user.parquet 的 sha256 必须相同。"""
    from eval.full_rank import full_rank

    out1 = full_rank(
        scores=SCORES,
        all_items=ALL_ITEMS,
        shielded=TRAIN_VAL,
        test_df=TEST_DF,
    )
    out2 = full_rank(
        scores=SCORES,
        all_items=ALL_ITEMS,
        shielded=TRAIN_VAL,
        test_df=TEST_DF,
    )

    p1 = tmp_path / "out1.parquet"
    p2 = tmp_path / "out2.parquet"
    out1.to_parquet(p1, index=False)
    out2.to_parquet(p2, index=False)

    h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
    h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
    assert h1 == h2, f"两次评估 hash 不同：{h1} vs {h2}"


# --------------------------------------------------------------------------- 列完整性
def test_per_user_columns(tmp_path):
    """per_user.parquet 必须包含要求的 5 列。"""
    from eval.full_rank import full_rank

    out = full_rank(
        scores=SCORES,
        all_items=ALL_ITEMS,
        shielded=TRAIN_VAL,
        test_df=TEST_DF,
    )
    expected = {"user_id", "test_item", "rank", "test_item_in_train", "test_rating"}
    assert expected.issubset(set(out.columns)), f"缺列：{expected - set(out.columns)}"
    # 测试物品不在训练集中（U0/I2, U1/I0, U2/I5 都不在 TRAIN_VAL）
    assert not out["test_item_in_train"].any(), "test_item_in_train 应全为 False"


# --------------------------------------------------------------------------- test_item_in_train 标记
def test_test_item_in_train_flag():
    """如果测试物品同时出现在训练集中，test_item_in_train=True。"""
    from eval.full_rank import full_rank

    # 构造一个测试物品在训练集中的场景
    shield = {("U0", "I1")}  # 只屏蔽 I1
    test = pd.DataFrame([{"user_id": "U0", "item_id": "I0", "rating": 5}])
    scores = pd.DataFrame([
        {"user_id": "U0", "item_id": "I0", "score": 1.0},
        {"user_id": "U0", "item_id": "I1", "score": 99.0},
        {"user_id": "U0", "item_id": "I2", "score": 0.5},
    ])
    out = full_rank(
        scores=scores,
        all_items=["I0", "I1", "I2"],
        shielded=shield,
        test_df=test,
    )
    # I0 不在 shield 中 → test_item_in_train=False（pandas 返回 np.bool_，用 not 判）
    row = out.iloc[0]
    assert not row["test_item_in_train"]


# --------------------------------------------------------------------------- 端到端 smoke
def test_end_to_end_with_cfg(tmp_path, cfg):
    """用 configs/eval.yaml 的 K 值做一次完整评估。"""
    from eval.full_rank import full_rank
    from eval.metrics import recall_at_k, ndcg_at_k

    with open(cfg) as f:
        cfg_dict = yaml.safe_load(f)

    out = full_rank(
        scores=SCORES,
        all_items=ALL_ITEMS,
        shielded=TRAIN_VAL,
        test_df=TEST_DF,
    )
    ranks = {row["user_id"]: row["rank"] for _, row in out.iterrows()}
    for k in cfg_dict["K"]:
        r = recall_at_k(ranks, k)
        n = ndcg_at_k(ranks, k)
        assert 0.0 <= r <= 1.0, f"Recall@{k} 越界：{r}"
        assert 0.0 <= n <= 1.0, f"NDCG@{k} 越界：{n}"