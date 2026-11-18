"""S1-c 配对检验测试：eval/paired_test.py

覆盖：
    - d_z = t / sqrt(n)，n 为用户数（不是 seed 数）
    - 跨 seed 先对每用户取平均 rank，再做配对检验
    - 两个模型用户集合不一致时取交集，并在 JSON 里报告 n_dropped
    - Recall@K 由 rank <= K 得到，与 eval/metrics.py 一致
    - Wilcoxon 符号秩检验在全部同号差时给出正确 p 值
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from eval.metrics import recall_at_k  # noqa: E402
from eval import paired_test as pt  # noqa: E402


# --------------------------------------------------------------------------- 构造数据
def _per_user(ranks):
    """{user_id: rank} → per_user DataFrame（单 seed）。"""
    return pd.DataFrame(
        {"user_id": list(ranks), "rank": list(ranks.values())}
    )


def _two_seeds_better_model():
    """模型 A 每用户 rank 3/5，模型 B rank 8/10 —— A 显著更好。"""
    users = [f"u{i}" for i in range(10)]
    a1 = {u: 3 for u in users}
    a2 = {u: 5 for u in users}
    b1 = {u: 8 for u in users}
    b2 = {u: 10 for u in users}
    return [_per_user(a1), _per_user(a2)], [_per_user(b1), _per_user(b2)]


# --------------------------------------------------------------------------- d_z 公式
def test_dz_equals_t_over_sqrt_n():
    """d_z = t / sqrt(n)，n 为用户数。手算一组已知数据核对。"""
    # 差值为 -5，常数 → 均值 -5，标准差 0 时 t 无穷；换一组有方差的
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = np.array([2.0, 3.0, 4.0, 5.0, 7.0])
    result = pt.paired_test_arrays(a, b)
    n = len(a)
    t, p = sps.ttest_rel(a, b)
    assert result["n"] == n
    assert result["t"] == pytest.approx(t)
    assert result["d_z"] == pytest.approx(t / math.sqrt(n))
    assert result["p_t"] == pytest.approx(p)


def test_dz_formula_small_n():
    """n=4 的小样本，d_z 仍按 n 而不是 n-1。"""
    a = np.array([0.1, 0.2, 0.3, 0.4])
    b = np.array([0.2, 0.2, 0.4, 0.5])
    result = pt.paired_test_arrays(a, b)
    t, _ = sps.ttest_rel(a, b)
    assert result["d_z"] == pytest.approx(t / math.sqrt(4))


# --------------------------------------------------------------------------- seed 平均
def test_seed_averaging_before_test():
    """先对每用户跨 seed 取平均 rank，再判断是否命中；而不是先按 seed 算指标再平均。"""
    users = [f"u{i}" for i in range(10)]
    # A：seed0 全部 rank=3；seed1 前 5 用户 rank=25，后 5 用户 rank=5
    #    平均后：前 5 = (3+25)/2 = 14 → 未命中；后 5 = (3+5)/2 = 4 → 命中
    # B：全部 rank=12 → 全部未命中
    a0 = _per_user({u: 3 for u in users})
    a1 = _per_user({**{u: 25 for u in users[:5]}, **{u: 5 for u in users[5:]}})
    b = [_per_user({u: 12 for u in users}) for _ in range(2)]

    result = pt.compare([a0, a1], b)

    assert result["n"] == 10
    # 先平均 rank 再命中 → 0.5；若先按 seed 算 Recall 再平均会得到 (1.0 + 0.5)/2 = 0.75
    assert result["mean_a"] == pytest.approx(0.5)
    assert result["mean_b"] == pytest.approx(0.0)
    assert result["delta"] == pytest.approx(0.5)
    assert result["seeds_a"] == 2
    assert result["seeds_b"] == 2


def test_seed_averaging_when_seeds_disagree():
    """两个 seed 的 rank 方向相反时，平均后仍按用户配对。"""
    a = [
        _per_user({"u0": 2, "u1": 20, "u2": 3, "u3": 40}),
        _per_user({"u0": 20, "u1": 2, "u2": 3, "u3": 40}),
    ]
    b = [
        _per_user({"u0": 12, "u1": 12, "u2": 12, "u3": 12}),
        _per_user({"u0": 12, "u1": 12, "u2": 12, "u3": 12}),
    ]
    result = pt.compare(a, b)
    # u0/u1 平均 rank = 11 → 未命中；u2 = 3 → 命中；u3 = 40 → 未命中
    assert result["mean_a"] == pytest.approx(0.25)
    assert result["mean_b"] == pytest.approx(0.0)


# --------------------------------------------------------------------------- 交集合
def test_intersection_of_users_and_n_dropped():
    """两模型用户集合不同时取交集，n_dropped 记账。"""
    a = [_per_user({"u0": 1, "u1": 2, "u2": 3})]
    b = [_per_user({"u1": 1, "u2": 2, "u3": 3})]
    result = pt.compare(a, b)
    assert result["n"] == 2
    assert result["n_dropped"] == 2  # u0 只在 A，u3 只在 B


# --------------------------------------------------------------------------- 指标口径
def test_recall_matches_metrics_module():
    """paired_test 的 Recall@K 必须与 eval/metrics.py 完全一致。"""
    a = [_per_user({f"u{i}": i + 1 for i in range(20)})]
    b = [_per_user({f"u{i}": i + 11 for i in range(20)})]
    result = pt.compare(a, b, k=10)

    ranks_a = {f"u{i}": i + 1 for i in range(20)}
    ranks_b = {f"u{i}": i + 11 for i in range(20)}
    assert result["metric"] == "Recall@10"
    assert result["mean_a"] == pytest.approx(recall_at_k(ranks_a, 10))
    assert result["mean_b"] == pytest.approx(recall_at_k(ranks_b, 10))


def test_ndcg_metric_selection():
    a = [_per_user({f"u{i}": i + 1 for i in range(20)})]
    b = [_per_user({f"u{i}": i + 11 for i in range(20)})]
    result = pt.compare(a, b, k=10, metric="NDCG")
    assert result["metric"] == "NDCG@10"
    assert 0.0 <= result["mean_a"] <= 1.0


# --------------------------------------------------------------------------- Wilcoxon
def test_wilcoxon_all_positive_differences():
    """全部差值同号时 Wilcoxon 双侧 p 应为最小值量级。"""
    a = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
    b = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = pt.paired_test_arrays(a, b)
    _, p_w = sps.wilcoxon(a, b)
    assert result["wilcoxon_p"] == pytest.approx(p_w)


def test_wilcoxon_zero_differences_handled():
    """全部差值同为 0 时不应抛异常，p 记为 1.0。"""
    a = np.array([5.0, 5.0, 5.0, 5.0])
    b = np.array([5.0, 5.0, 5.0, 5.0])
    result = pt.paired_test_arrays(a, b)
    assert result["wilcoxon_p"] == pytest.approx(1.0)
    assert result["delta"] == pytest.approx(0.0)


def test_degenerate_constant_difference():
    """所有用户差值完全相同：方差为 0，t/d_z 记 None，不能写成 inf/nan（JSON 无法序列化）。"""
    a = np.array([10.0, 11.0, 12.0])
    b = np.array([1.0, 2.0, 3.0])
    result = pt.paired_test_arrays(a, b)

    assert result["degenerate"] is True
    assert result["delta"] == pytest.approx(9.0)
    assert result["t"] is None
    assert result["d_z"] is None
    assert result["p_t"] == pytest.approx(0.0)


def test_non_degenerate_flags_false():
    a = np.array([3.0, 4.0, 5.0])
    b = np.array([1.0, 2.0, 2.0])
    result = pt.paired_test_arrays(a, b)
    assert result["degenerate"] is False
    assert result["t"] is not None


# --------------------------------------------------------------------------- 输出 JSON
def test_json_output_schema(tmp_path):
    a_seeds, b_seeds = _two_seeds_better_model()
    out = tmp_path / "paired.json"
    pt.compare_and_write(a_seeds, b_seeds, out_path=out)

    import json
    d = json.loads(out.read_text(encoding="utf-8"))
    for key in ("metric", "n", "mean_a", "mean_b", "delta", "t", "p_t",
                "d_z", "wilcoxon_p", "seeds_a", "seeds_b", "n_dropped", "degenerate"):
        assert key in d, f"输出缺字段 {key}"
    assert d["n"] == 10


def test_reads_per_user_parquet_from_seed_dirs(tmp_path):
    """compare_from_dirs 能从 results/{exp}/{model}/seed*/per_user.parquet 读。"""
    ranks_b = [12, 3, 14, 5, 16, 7, 18, 9]  # 一半命中 Recall@10
    for seed in (0, 1):
        d = tmp_path / "recall_main" / "modelA" / f"seed{seed}"
        d.mkdir(parents=True)
        pd.DataFrame({"user_id": [f"u{i}" for i in range(8)],
                      "rank": [3] * 8}).to_parquet(d / "per_user.parquet")

        d = tmp_path / "recall_main" / "modelB" / f"seed{seed}"
        d.mkdir(parents=True)
        pd.DataFrame({"user_id": [f"u{i}" for i in range(8)],
                      "rank": ranks_b}).to_parquet(d / "per_user.parquet")

    result = pt.compare_from_dirs(
        dir_a=tmp_path / "recall_main" / "modelA",
        dir_b=tmp_path / "recall_main" / "modelB",
        k=10,
    )
    assert result["n"] == 8
    assert result["seeds_a"] == 2
    assert result["seeds_b"] == 2
    assert result["mean_a"] == pytest.approx(1.0)   # rank=3 全部命中
    assert result["mean_b"] == pytest.approx(0.5)   # 8 个里 4 个 <=10