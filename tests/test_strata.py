"""S1-c 冷启动分层测试：eval/strata.py

覆盖：
    - 四层边界：0-4 / 5-9 / 10-29 / >=30，边界值归属正确（与论文表 3-11 一致）
    - 分层按训练集交互数（不含测试交互）划分
    - 按人数加权的层均值 == 整体指标（差 < 1e-9）
    - 层内 Recall@K / NDCG@K 与 eval/metrics.py 逐层重算一致
    - 空层输出 n=0 且指标为 null，不报错
    - per_user 中出现在 train 之外的用户 → 显式报错
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from eval.metrics import ndcg_at_k, recall_at_k  # noqa: E402
from eval import strata as st  # noqa: E402


# --------------------------------------------------------------------------- 构造
def _train_df(user_counts: dict) -> pd.DataFrame:
    """按 {user_id: 交互数} 造出最小的训练集 DataFrame。"""
    rows = []
    for u, n in user_counts.items():
        for i in range(n):
            rows.append({"user_id": u, "item_id": f"{u}_i{i}"})
    return pd.DataFrame(rows)


def _per_user(ranks: dict) -> pd.DataFrame:
    return pd.DataFrame({"user_id": list(ranks), "rank": list(ranks.values())})


def _edge_counts() -> dict:
    """覆盖每个层边界：3,4 / 5,9 / 10,29 / 30,31。

    0-4 层用 3 与 4：训练集 5-core 过滤后最小交互数为 3，0 条交互的用户
    不可能出现在 train.parquet 里（per_user 会因找不到该用户而报错）。
    """
    return {
        "u3": 3, "u4": 4,
        "u5": 5, "u9": 9,
        "u10": 10, "u29": 29,
        "u30": 30, "u31": 31,
    }


# --------------------------------------------------------------------------- 分层边界
def test_layer_boundaries():
    """边界值恰好落在预期的层里。"""
    counts = _edge_counts()
    ranks = {u: 1 for u in counts}
    result = st.compute_strata(_per_user(ranks), _train_df(counts), ks=(10,))

    assert set(result["layers"]) == {"0-4", "5-9", "10-29", ">=30"}
    assert result["layers"]["0-4"]["n"] == 2       # u3, u4
    assert result["layers"]["5-9"]["n"] == 2       # u5, u9
    assert result["layers"]["10-29"]["n"] == 2     # u10, u29
    assert result["layers"][">=30"]["n"] == 2      # u30, u31
    assert result["n"] == 8


def test_no_user_dropped():
    """所有用户都必须被分到某一层，不丢人。"""
    counts = _edge_counts()
    result = st.compute_strata(
        _per_user({u: 5 for u in counts}), _train_df(counts), ks=(10,)
    )
    total = sum(v["n"] for v in result["layers"].values())
    assert total == result["n"] == len(counts)


def test_strata_uses_train_counts_not_per_user_df():
    """分层依据是训练集交互数：同一 per_user 排名，训练集不同则层不同。"""
    ranks = _per_user({"u": 1})
    r_small = st.compute_strata(ranks, _train_df({"u": 4}), ks=(10,))
    r_big = st.compute_strata(ranks, _train_df({"u": 40}), ks=(10,))
    assert r_small["layers"]["0-4"]["n"] == 1
    assert r_big["layers"][">=30"]["n"] == 1


def test_train_pairs_dedupe_not_required_but_counts_rows():
    """训练交互数按行计（LOO 下 (user,item) 唯一，行数即对数）。"""
    counts = {"u": 10}
    df = _train_df(counts)
    result = st.compute_strata(_per_user({"u": 1}), df, ks=(10,))
    assert result["layers"]["10-29"]["n"] == 1


# --------------------------------------------------------------------------- 守恒
def test_weighted_mean_equals_overall_recall():
    """Σ n_i · Recall_i / Σ n_i == 整体 Recall（差 < 1e-9）。"""
    counts = {"a": 3, "b": 3, "c": 8, "d": 8, "e": 15, "f": 40}
    ranks = {"a": 1, "b": 50, "c": 5, "d": 12, "e": 30, "f": 2}
    result = st.compute_strata(_per_user(ranks), _train_df(counts), ks=(10, 20))

    layers = result["layers"]
    non_empty = [v for v in layers.values() if v["n"] > 0]  # 空层指标为 None，不参与加权
    n_total = sum(v["n"] for v in non_empty)

    for k in (10, 20):
        weighted = sum(v["n"] * v["metrics"][f"Recall@{k}"] for v in non_empty) / n_total
        overall = result["overall"][f"Recall@{k}"]
        assert abs(weighted - overall) < 1e-9, f"Recall@{k} 守恒失败"

        weighted_ndcg = sum(v["n"] * v["metrics"][f"NDCG@{k}"] for v in non_empty) / n_total
        overall_ndcg = result["overall"][f"NDCG@{k}"]
        assert abs(weighted_ndcg - overall_ndcg) < 1e-9, f"NDCG@{k} 守恒失败"


def test_assert_conservation_raises_on_mismatch():
    """守恒检查器在人为篡改时抛错。"""
    counts = {"a": 3, "b": 8}
    ranks = {"a": 1, "b": 2}
    result = st.compute_strata(_per_user(ranks), _train_df(counts), ks=(10,))
    result["layers"]["0-4"]["metrics"]["Recall@10"] = 0.999  # 篡改
    with pytest.raises(AssertionError):
        st.assert_conservation(result, tol=1e-9)


def test_assert_conservation_passes_on_clean_result():
    counts = {"a": 3, "b": 8, "c": 40}
    ranks = {"a": 1, "b": 12, "c": 2}
    result = st.compute_strata(_per_user(ranks), _train_df(counts), ks=(10, 20))
    st.assert_conservation(result, tol=1e-9)  # 不应抛错


# --------------------------------------------------------------------------- 层内指标
def test_layer_metrics_match_metrics_module():
    """每层指标必须与直接用 eval/metrics.py 重算一致。"""
    counts = {"a": 3, "b": 3, "c": 12, "d": 12}
    ranks = {"a": 1, "b": 15, "c": 7, "d": 25}
    result = st.compute_strata(_per_user(ranks), _train_df(counts), ks=(10,))

    for layer, members in (
        ("0-4", ["a", "b"]),
        ("10-29", ["c", "d"]),
    ):
        sub = {u: ranks[u] for u in members}
        assert result["layers"][layer]["metrics"]["Recall@10"] == pytest.approx(
            recall_at_k(sub, 10)
        )


def test_ndcg_in_layers():
    counts = {"a": 3, "b": 3}
    ranks = {"a": 1, "b": 2}
    result = st.compute_strata(_per_user(ranks), _train_df(counts), ks=(10,))
    assert result["layers"]["0-4"]["metrics"]["NDCG@10"] == pytest.approx(
        ndcg_at_k(ranks, 10)
    )


# --------------------------------------------------------------------------- 空层与异常
def test_empty_layer_reports_zero_and_null():
    """没有用户落入的层：n=0，指标为 None。"""
    counts = {"a": 3, "b": 30}
    result = st.compute_strata(_per_user({"a": 1, "b": 2}), _train_df(counts), ks=(10,))
    assert result["layers"]["10-29"]["n"] == 0
    assert result["layers"]["10-29"]["metrics"]["Recall@10"] is None


def test_user_missing_from_train_raises():
    """per_user 里有 train 里没有的用户 → 显式报错，不静默丢弃。"""
    with pytest.raises(KeyError, match="u_ghost"):
        st.compute_strata(_per_user({"u_ghost": 1}), _train_df({"a": 3}), ks=(10,))


def test_empty_per_user_raises():
    with pytest.raises(ValueError):
        st.compute_strata(_per_user({}), _train_df({"a": 3}), ks=(10,))


# --------------------------------------------------------------------------- CLI 读取
def test_compute_strata_from_files(tmp_path):
    """能从 per_user.parquet + train.parquet 路径直接算。"""
    pd.DataFrame({"user_id": ["a", "b"], "rank": [1, 9]}).to_parquet(
        tmp_path / "per_user.parquet"
    )
    _train_df({"a": 3, "b": 20}).to_parquet(tmp_path / "train.parquet")

    result = st.compute_strata_from_files(
        per_user_path=tmp_path / "per_user.parquet",
        train_path=tmp_path / "train.parquet",
        ks=(10,),
    )
    assert result["layers"]["0-4"]["n"] == 1
    assert result["layers"]["10-29"]["n"] == 1
    assert result["overall"]["Recall@10"] == pytest.approx(1.0)  # 两个 rank 都 <= 10