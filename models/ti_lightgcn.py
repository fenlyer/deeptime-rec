# -*- coding: utf-8 -*-
"""TI-LightGCN: 时间感知反馈加权图协同过滤模型

在 LightGCN 的邻域聚合中引入统一边权重函数：
    w(u,i) = α_r × exp(-λ × (T_now - t) / T)

其中：
- α_r：评分反馈强度（表 3-1: 5→3.0, 4→1.5, 3→1.0, 1-2→0.1）
- λ：时间衰减率（默认 0.001）
- T_now：数据集最大时间戳
- T：时间归一化常数（86400 秒/天）
- t：交互时间戳

归一化传播使用加权度：
    ê_u^(l) = Σ_{i∈N_u} w(u,i) / √W_u × √W_i × ê_i^(l-1)
其中 W_u = Σ_{i∈N_u} w(u,i) 为用户 u 的加权度。

论文：式 (3-1) ~ (3-5)，表 3-1。
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import torch

# RecBole 环境可能未安装时做条件导入
try:
    from recbole.model.general_recommender.lightgcn import LightGCN
    from recbole.model.loss import BPRLoss, EmbLoss
    from recbole.model.init import xavier_uniform_initialization
    from recbole.utils import InputType
    _RECBOLE_AVAILABLE = True
except ImportError:
    _RECBOLE_AVAILABLE = False
    LightGCN = object  # type: ignore


if _RECBOLE_AVAILABLE:

    class TILightGCN(LightGCN):
        """时间感知反馈加权 LightGCN。

        继承 RecBole LightGCN，重写 get_norm_adj_mat() 实现加权边。
        训练损失与标准 LightGCN 相同（BPR + L2），长尾正则 γ=0 时不生效。
        """

        def __init__(self, config, dataset):
            # 读取 TI-LightGCN 专有参数
            # RecBole Config 不支持 .get()，用 __getitem__ + 默认值
            self.lambda_ = float(config["lambda_"] if "lambda_" in config else 0.001)
            self.gamma = float(config["gamma"] if "gamma" in config else 0.0)
            self.theta = int(config["theta"] if "theta" in config else 10)

            # 读取训练集边权数据（从 processed/IS/train.parquet）
            # 注意：必须在 super().__init__() 之前设置，因为 super 会调 get_norm_adj_mat()
            self._ti_data_path = self._resolve_ti_data_path(config)
            self._ti_edge_data = self._load_edge_data()

            # 调用父类初始化（会调 get_norm_adj_mat）
            super().__init__(config, dataset)

        def _resolve_ti_data_path(self, config) -> Path:
            """定位 data/processed/IS/train.parquet"""
            # 优先从 config 读取，否则用仓库相对路径
            if "ti_data_path" in config:
                return Path(config["ti_data_path"])
            # 默认路径：仓库根/data/processed/IS/train.parquet
            repo_root = Path(__file__).resolve().parent.parent
            return repo_root / "data" / "processed" / "IS" / "train.parquet"

        def _load_edge_data(self) -> dict:
            """从 train.parquet 加载边权计算所需数据。

            Returns:
                dict with keys: user_idx, item_idx, alpha, timestamp, t_now
            """
            import pandas as pd

            df = pd.read_parquet(self._ti_data_path)
            return {
                "user_idx": df["user_idx"].values.astype(np.int64),
                "item_idx": df["item_idx"].values.astype(np.int64),
                "alpha": df["alpha"].values.astype(np.float32),
                "timestamp": df["timestamp"].values.astype(np.int64),
                "t_now": int(df["timestamp"].max()),
            }

        def _compute_edge_weights(self) -> np.ndarray:
            """计算所有边的权重：w = α_r × exp(-λ × (T_now - t) / T)"""
            d = self._ti_edge_data
            delta_t = d["t_now"] - d["timestamp"]
            weights = d["alpha"] * np.exp(-self.lambda_ * delta_t / 86400)
            return weights.astype(np.float32)

        def get_norm_adj_mat(self):
            """构建加权归一化邻接矩阵 D_w^{-0.5} × A_w × D_w^{-0.5}。

            重写 LightGCN.get_norm_adj_mat()，将二值边替换为加权边。
            """
            n_users = self.n_users
            n_items = self.n_items
            N = n_users + n_items

            # 计算边权
            weights = self._compute_edge_weights()
            user_idx = self._ti_edge_data["user_idx"]
            item_idx = self._ti_edge_data["item_idx"]

            # 构建加权邻接矩阵 A_w（对称：user→item 和 item→user）
            A = sp.dok_matrix((N, N), dtype=np.float32)
            for u, i, w in zip(user_idx, item_idx, weights):
                A[u, n_users + i] = w
                A[n_users + i, u] = w
            A = A.tocsr()

            # 加权度 W = Σ w(u,i)
            W = np.array(A.sum(axis=1)).flatten()

            # D^{-0.5}
            d_inv_sqrt = np.zeros(N, dtype=np.float32)
            nonzero = W > 0
            d_inv_sqrt[nonzero] = W[nonzero] ** (-0.5)
            D_inv_sqrt = sp.diags(d_inv_sqrt)

            # 归一化：Â = D^{-0.5} × A_w × D^{-0.5}
            L = D_inv_sqrt @ A @ D_inv_sqrt
            L = L.tocoo()

            # 转为 PyTorch sparse tensor
            row = L.row
            col = L.col
            indices = torch.LongTensor(np.array([row, col]))
            data = torch.FloatTensor(L.data)
            sparse_L = torch.sparse.FloatTensor(indices, data, torch.Size(L.shape))

            return sparse_L

        def calculate_loss(self, interaction):
            """BPR 损失 + L2 正则 + 长尾正则（γ > 0 时生效）。

            MVP 阶段 gamma=0，长尾正则不生效。
            """
            # 清除缓存（训练时每 batch 需要重新计算）
            if self.restore_user_e is not None or self.restore_item_e is not None:
                self.restore_user_e, self.restore_item_e = None, None

            user = interaction[self.USER_ID]
            pos_item = interaction[self.ITEM_ID]
            neg_item = interaction[self.NEG_ITEM_ID]

            user_all_embeddings, item_all_embeddings = self.forward()
            u_embeddings = user_all_embeddings[user]
            pos_embeddings = item_all_embeddings[pos_item]
            neg_embeddings = item_all_embeddings[neg_item]

            # BPR 损失
            pos_scores = torch.mul(u_embeddings, pos_embeddings).sum(dim=1)
            neg_scores = torch.mul(u_embeddings, neg_embeddings).sum(dim=1)
            mf_loss = self.mf_loss(pos_scores, neg_scores)

            # L2 正则
            u_ego = self.user_embedding(user)
            pos_ego = self.item_embedding(pos_item)
            neg_ego = self.item_embedding(neg_item)
            reg_loss = self.reg_loss(u_ego, pos_ego, neg_ego, require_pow=self.require_pow)

            loss = mf_loss + self.reg_weight * reg_loss

            # 长尾正则（gamma > 0 时）
            if self.gamma > 0:
                loss = loss + self.gamma * self._long_tail_reg_loss(item_all_embeddings)

            return loss

        def _long_tail_reg_loss(self, item_embeddings: torch.Tensor) -> torch.Tensor:
            """长尾商品正则：约束长尾物品的图嵌入接近语义嵌入。

            MVP 阶段返回 0（需要 Sentence-BERT 语义嵌入才能实现）。
            消融实验卡片 S-recall-ablation 再补充实现。
            """
            # TODO: S-recall-ablation 实现
            # 1. 加载 item_meta.parquet 的 sentence-bert 嵌入
            # 2. 投影到 d 维
            # 3. 找出交互次数 < theta 的长尾物品
            # 4. 计算 ||e_i - e_i_sem||^2 之和
            return torch.tensor(0.0, device=item_embeddings.device)

else:
    # RecBole 未安装时的占位类（用于测试导入）
    class TILightGCN:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "RecBole 未安装。请在 recbole_env 环境中运行："
                "conda activate recbole_env"
            )
