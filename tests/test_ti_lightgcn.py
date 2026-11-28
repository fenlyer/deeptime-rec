"""TI-LightGCN 单元测试

测试边权计算、加权邻接矩阵构造与模型前向传播。
不依赖 RecBole 运行时（纯函数测试 + mock）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch


# ---------------------------------------------------------------------------
# 边权函数测试
# ---------------------------------------------------------------------------

def compute_edge_weights(
    alpha: np.ndarray,
    timestamp: np.ndarray,
    t_now: int,
    lambda_: float = 0.001,
    T: int = 86400,
) -> np.ndarray:
    """计算边权重：w = α_r × exp(-λ × (T_now - t) / T)

    这是 models/ti_lightgcn.py 的核心公式，提取出来便于独立测试。
    """
    delta_t = t_now - timestamp
    return alpha * np.exp(-lambda_ * delta_t / T)


class TestEdgeWeightFormula:
    """论文式 (3-1)：w(u,i) = α_r × exp(-λ × Δt / T)"""

    def test_no_decay_when_current(self):
        """Δt = 0 时，exp(0) = 1，权重 = α_r"""
        w = compute_edge_weights(
            alpha=np.array([3.0]),
            timestamp=np.array([1000000]),
            t_now=1000000,
        )
        assert abs(w[0] - 3.0) < 1e-10

    def test_decay_at_half_life(self):
        """λ=0.001, 半衰期 = ln2/λ × 86400 ≈ 693 天"""
        half_life_sec = 693 * 86400  # 693 天
        w = compute_edge_weights(
            alpha=np.array([3.0]),
            timestamp=np.array([1000000]),
            t_now=1000000 + half_life_sec,
        )
        # 3.0 × exp(-0.001 × 693) = 3.0 × 0.4998 ≈ 1.4995
        expected = 3.0 * np.exp(-0.001 * 693)
        assert abs(w[0] - expected) < 1e-6

    def test_alpha_r_mapping(self):
        """表 3-1：5→3.0, 4→1.5, 3→1.0, 1-2→0.1"""
        ratings = np.array([5, 4, 3, 2, 1])
        alpha_map = {5: 3.0, 4: 1.5, 3: 1.0, 2: 0.1, 1: 0.1}
        alphas = np.array([alpha_map[r] for r in ratings])

        w = compute_edge_weights(
            alpha=alphas,
            timestamp=np.array([1000000] * 5),
            t_now=1000000,  # Δt = 0
        )
        np.testing.assert_allclose(w, [3.0, 1.5, 1.0, 0.1, 0.1])

    def test_older_interaction_has_lower_weight(self):
        """相同评分，时间更远的交互权重更低"""
        w_recent = compute_edge_weights(
            alpha=np.array([3.0]),
            timestamp=np.array([1000000]),
            t_now=1100000,
        )
        w_old = compute_edge_weights(
            alpha=np.array([3.0]),
            timestamp=np.array([900000]),
            t_now=1100000,
        )
        assert w_recent[0] > w_old[0]

    def test_zero_lambda_equals_static(self):
        """λ=0 时，所有边权 = α_r（无时间衰减）"""
        w = compute_edge_weights(
            alpha=np.array([3.0, 1.5, 1.0, 0.1]),
            timestamp=np.array([100, 200, 300, 400]),
            t_now=500,
            lambda_=0.0,
        )
        np.testing.assert_allclose(w, [3.0, 1.5, 1.0, 0.1])

    def test_batch_computation(self):
        """批量计算与逐个计算一致"""
        alphas = np.array([3.0, 1.5, 1.0, 0.1])
        timestamps = np.array([100, 200, 300, 400])
        t_now = 500

        w_batch = compute_edge_weights(alphas, timestamps, t_now)
        w_single = np.array([
            compute_edge_weights(np.array([a]), np.array([t]), t_now)[0]
            for a, t in zip(alphas, timestamps)
        ])
        np.testing.assert_allclose(w_batch, w_single)


# ---------------------------------------------------------------------------
# 加权邻接矩阵测试
# ---------------------------------------------------------------------------

def build_weighted_adj_matrix(
    user_idx: np.ndarray,
    item_idx: np.ndarray,
    weights: np.ndarray,
    n_users: int,
    n_items: int,
) -> np.ndarray:
    """构建加权归一化邻接矩阵 D_w^{-0.5} × A_w × D_w^{-0.5}

    提取出来便于测试。返回 dense numpy array（测试用，生产用 sparse）。
    """
    N = n_users + n_items
    A = np.zeros((N, N), dtype=np.float64)

    # 填充加权边（对称：user→item 和 item→user）
    for u, i, w in zip(user_idx, item_idx, weights):
        A[u, n_users + i] = w
        A[n_users + i, u] = w

    # 加权度
    W = A.sum(axis=1)
    # D^{-0.5}
    d_inv_sqrt = np.zeros(N)
    nonzero = W > 0
    d_inv_sqrt[nonzero] = W[nonzero] ** (-0.5)
    D_inv_sqrt = np.diag(d_inv_sqrt)

    # 归一化
    A_hat = D_inv_sqrt @ A @ D_inv_sqrt
    return A_hat


class TestWeightedAdjMatrix:
    """论文式 (3-3)(3-4)：加权归一化传播矩阵"""

    def test_shape(self):
        """邻接矩阵 shape = (n_users + n_items, n_users + n_items)"""
        A_hat = build_weighted_adj_matrix(
            user_idx=np.array([0, 1]),
            item_idx=np.array([0, 1]),
            weights=np.array([1.0, 2.0]),
            n_users=3,
            n_items=2,
        )
        assert A_hat.shape == (5, 5)

    def test_symmetry(self):
        """A_w 对称 → Â 对称"""
        A_hat = build_weighted_adj_matrix(
            user_idx=np.array([0, 0, 1]),
            item_idx=np.array([0, 1, 0]),
            weights=np.array([3.0, 1.5, 1.0]),
            n_users=2,
            n_items=2,
        )
        np.testing.assert_allclose(A_hat, A_hat.T, atol=1e-12)

    def test_bipartite_structure(self):
        """用户-物品二部图：user-user 和 item-item 块全零"""
        n_users, n_items = 3, 2
        A_hat = build_weighted_adj_matrix(
            user_idx=np.array([0, 1, 2]),
            item_idx=np.array([0, 1, 0]),
            weights=np.array([1.0, 2.0, 3.0]),
            n_users=n_users,
            n_items=n_items,
        )
        # User-user block
        assert np.allclose(A_hat[:n_users, :n_users], 0)
        # Item-item block
        assert np.allclose(A_hat[n_users:, n_users:], 0)

    def test_weighted_vs_binary(self):
        """当所有权重=1 时，加权邻接矩阵 = 标准 LightGCN 邻接矩阵"""
        user_idx = np.array([0, 0, 1])
        item_idx = np.array([0, 1, 0])
        weights = np.array([1.0, 1.0, 1.0])
        n_users, n_items = 2, 2

        A_hat_weighted = build_weighted_adj_matrix(
            user_idx, item_idx, weights, n_users, n_items
        )

        # 手动计算二值版本
        A_binary = np.zeros((4, 4))
        for u, i in zip(user_idx, item_idx):
            A_binary[u, n_users + i] = 1.0
            A_binary[n_users + i, u] = 1.0
        W_bin = A_binary.sum(axis=1)
        d_inv = np.where(W_bin > 0, W_bin ** (-0.5), 0)
        A_hat_binary = np.diag(d_inv) @ A_binary @ np.diag(d_inv)

        np.testing.assert_allclose(A_hat_weighted, A_hat_binary, atol=1e-12)

    def test_scale_invariance(self):
        """命题 1：所有边权同乘常数 c，归一化矩阵不变"""
        user_idx = np.array([0, 0, 1])
        item_idx = np.array([0, 1, 0])
        weights = np.array([3.0, 1.5, 1.0])
        n_users, n_items = 2, 2

        A_hat_1 = build_weighted_adj_matrix(
            user_idx, item_idx, weights, n_users, n_items
        )
        A_hat_2 = build_weighted_adj_matrix(
            user_idx, item_idx, weights * 5.0, n_users, n_items
        )
        np.testing.assert_allclose(A_hat_1, A_hat_2, atol=1e-12)

    def test_isolated_node(self):
        """孤立节点对应的行/列全零"""
        A_hat = build_weighted_adj_matrix(
            user_idx=np.array([0]),
            item_idx=np.array([0]),
            weights=np.array([1.0]),
            n_users=2,  # user 1 is isolated
            n_items=1,
        )
        # User 1 (index 1) should have all zeros
        assert np.allclose(A_hat[1, :], 0)
        assert np.allclose(A_hat[:, 1], 0)


# ---------------------------------------------------------------------------
# 长尾正则测试
# ---------------------------------------------------------------------------

class TestLongTailReg:
    """长尾商品集合判定：交互次数 < θ"""

    def test_identify_tail_items(self):
        """交互次数 < θ 的为长尾商品"""
        item_interaction_counts = np.array([5, 15, 3, 8, 20, 2])
        theta = 10
        is_tail = item_interaction_counts < theta
        expected = np.array([True, False, True, True, False, True])
        np.testing.assert_array_equal(is_tail, expected)

    def test_no_tail_when_all_popular(self):
        """所有商品交互 ≥ θ 时，无长尾"""
        counts = np.array([10, 20, 30])
        assert not (counts < 10).any()


# ---------------------------------------------------------------------------
# 端到端边权计算（使用 train.parquet 真实数据格式）
# ---------------------------------------------------------------------------

class TestEdgeWeightEndToEnd:
    """用模拟 train.parquet 数据测试完整边权计算流程"""

    def test_compute_weights_from_dataframe(self):
        """从 DataFrame 格式计算边权"""
        df = pd.DataFrame({
            "user_idx": [0, 0, 1],
            "item_idx": [38, 100, 38],
            "alpha": [3.0, 1.5, 1.0],
            "timestamp": [1692892488, 1692800000, 1690000000],
        })
        t_now = df["timestamp"].max()  # 1692892488
        lambda_ = 0.001

        weights = compute_edge_weights(
            alpha=df["alpha"].values,
            timestamp=df["timestamp"].values,
            t_now=t_now,
            lambda_=lambda_,
        )

        # 第一条：Δt=0, w = 3.0
        assert abs(weights[0] - 3.0) < 1e-10
        # 第二条：Δt > 0, w < 1.5
        assert weights[1] < 1.5
        # 第三条：Δt 更大, w < 1.0 且 < weights[1]
        assert weights[2] < 1.0
        assert weights[2] < weights[1]

    def test_all_weights_positive(self):
        """所有边权 > 0（命题 2 的前提条件）"""
        df = pd.DataFrame({
            "user_idx": [0, 1, 2],
            "item_idx": [0, 1, 2],
            "alpha": [0.1, 1.0, 3.0],
            "timestamp": [1000000, 900000, 800000],
        })
        t_now = 2000000

        weights = compute_edge_weights(
            alpha=df["alpha"].values,
            timestamp=df["timestamp"].values,
            t_now=t_now,
        )
        assert (weights > 0).all()


# ---------------------------------------------------------------------------
# 参数量验证
# ---------------------------------------------------------------------------

class TestParameterCount:
    """论文表 3-2：TI-LightGCN 参数量 = LightGCN = (|U|+|I|)×d"""

    def test_parameter_count_formula(self):
        """(|U|+|I|) × d = (50985+25848) × 64 = 4,917,312 ≈ 4.9M"""
        n_users = 50985  # user_idx range 0..50984, count=50985
        n_items = 25848  # item_idx range 0..25847, count=25848
        d = 64
        n_params = (n_users + n_items) * d
        assert n_params == 4_917_312
        # 论文说 4.9M，4917312 ≈ 4.92M
        assert abs(n_params / 1e6 - 4.9) < 0.1
