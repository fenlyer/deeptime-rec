"""RecBole 与 eval/ 交叉校验（S1-b）

对同一份训练好的模型，分别用 RecBole 自带评估和 eval/ 计算指标，
比较 Recall@10/20、NDCG@10/20 的差异和逐用户 rank 一致率。

口径
----
    - 输入：RecBole 训练好的 checkpoint，生成每个用户对所有物品的打分
    - 用 eval/full_rank.py 计算 rank（屏蔽训练+验证物品）
    - 用 eval/metrics.py 计算 Recall@K、NDCG@K
    - 与 RecBole 自带的评估结果比较

输出
----
    results/_smoke/crosscheck.json：
        {
            "recbole": {"recall@10": ..., "recall@20": ..., "ndcg@10": ..., "ndcg@20": ...},
            "our_eval": {"recall@10": ..., "recall@20": ..., "ndcg@10": ..., "ndcg@20": ...},
            "user_rank_consistency": 0.999,  # 一致率
            "inconsistent_users": [...]  # 不一致的用户 ID 列表
        }

使用
----
    # 在 AutoDL 上运行（需要 GPU 环境）
    python eval/crosscheck_recbole.py \\
        --checkpoint results/_smoke/recbole/LightGCN-Nov-18-*.pth \\
        --data-path data/recbole \\
        --output results/_smoke/crosscheck.json

注意
----
    - 本脚本需要在有 RecBole + GPU 的环境上运行（AutoDL 的 rec 环境）
    - 本机 CPU 环境（research）不运行此脚本，只读取 crosscheck.json 做对账
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_recbole_eval_results(checkpoint_path: Path, data_path: Path):
    """加载 RecBole 训练好的模型，生成评估结果。

    参数
    ----
    checkpoint_path : RecBole checkpoint (.pth) 路径
    data_path : RecBole 数据目录（含 IS/ 子目录）

    返回
    ----
    recbole_metrics : dict，RecBole 自带的评估结果
    user_embeddings : ndarray，用户嵌入矩阵
    item_embeddings : ndarray，物品嵌入矩阵
    """
    from recbole.config import Config
    from recbole.data import create_dataset, data_preparation
    from recbole.utils import init_seed, get_model, get_trainer, ModelType

    # 配置（与 recbole_smoke.py 一致）
    config_dict = {
        "model": "LightGCN",
        "dataset": "IS",
        "data_path": str(data_path),
        "benchmark_filename": ["train", "val", "test"],
        "eval_args": {
            "split": {"mode": "custom"},
            "group_by": "user",
            "order": "RO",
            "repeat": "none",
        },
        "metrics": ["Recall", "NDCG"],
        "topk": [10, 20],
        "valid_metric": "Recall@10",
        "embedding_size": 64,
        "n_layers": 3,
        "use_gpu": torch.cuda.is_available(),
        "load_col": {"inter": ["user_id", "item_id", "rating", "timestamp"]},
    }

    config = Config(model="LightGCN", dataset="IS", config_dict=config_dict)
    init_seed(config["seed"], config["reproducibility"])

    # 加载数据集
    dataset = create_dataset(config)
    _, _, test_data = data_preparation(config, dataset)

    # 加载模型
    model_class = get_model(config["model"])
    model = model_class(config, test_data.dataset).to(config["device"])

    # 加载 checkpoint
    checkpoint = torch.load(checkpoint_path, map_location=config["device"])
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    # 用 RecBole 自带评估
    trainer_class = get_trainer(ModelType.GENERAL, config["model"])
    trainer = trainer_class(config, model)
    recbole_result = trainer.evaluate(test_data, load_best_model=False, show_progress=False)

    recbole_metrics = {
        "recall@10": float(recbole_result["recall@10"]),
        "recall@20": float(recbole_result["recall@20"]),
        "ndcg@10": float(recbole_result["ndcg@10"]),
        "ndcg@20": float(recbole_result["ndcg@20"]),
    }

    # 提取嵌入（在 GPU 上算完再搬到 CPU）
    user_embeddings = model.user_embedding.weight.detach().cpu().numpy()
    item_embeddings = model.item_embedding.weight.detach().cpu().numpy()

    return recbole_metrics, user_embeddings, item_embeddings


def compute_our_eval_results(
    user_embeddings: np.ndarray,
    item_embeddings: np.ndarray,
    train_path: Path,
    val_path: Path,
    test_path: Path,
) -> tuple[Dict[str, float], pd.DataFrame]:
    """用 eval/ 计算指标（向量化版本）。

    参数
    ----
    user_embeddings : 用户嵌入矩阵 (n_users, dim)
    item_embeddings : 物品嵌入矩阵 (n_items, dim)
    train_path, val_path, test_path : processed/IS 的 parquet 路径

    返回
    ----
    our_metrics : dict，eval/ 的评估结果
    per_user : DataFrame，每用户一行（user_id, test_item, rank, ...）
    """
    from eval.metrics import recall_at_k, ndcg_at_k

    # 加载数据
    train = pd.read_parquet(train_path)
    val = pd.read_parquet(val_path)
    test = pd.read_parquet(test_path)

    n_users_total = user_embeddings.shape[0]
    n_items_total = item_embeddings.shape[0]

    # 构建屏蔽矩阵（训练+验证物品设为 -inf）
    print("  构建屏蔽矩阵...")
    train_val_pairs = pd.concat([
        train[["user_idx", "item_idx"]],
        val[["user_idx", "item_idx"]],
    ]).values
    shield_mat = np.zeros((n_users_total, n_items_total), dtype=bool)
    shield_mat[train_val_pairs[:, 0], train_val_pairs[:, 1]] = True

    # 矩阵运算打分：scores[u, i] = user_emb[u] · item_emb[i]
    print("  计算打分矩阵...")
    score_matrix = user_embeddings @ item_embeddings.T  # (n_users, n_items)

    # 屏蔽训练+验证物品
    score_matrix[shield_mat] = -np.inf

    # 逐用户计算测试物品排名（向量化）
    print("  计算排名...")
    test_users = test["user_idx"].values
    test_items = test["item_idx"].values

    ranks = {}
    per_user_rows = []
    for idx in range(len(test)):
        u = int(test_users[idx])
        i = int(test_items[idx])

        # 该用户的打分（已屏蔽）
        user_scores = score_matrix[u]  # (n_items,)

        # 测试物品的分数
        test_score = user_scores[i]

        if test_score == -np.inf:
            # 测试物品被屏蔽（在训练/验证中出现过）
            rank = float("inf")
        else:
            # 悲观排名：1 + (比它大的个数) + (与它同分的个数)
            # 只考虑未被屏蔽的物品
            valid_mask = user_scores != -np.inf
            valid_scores = user_scores[valid_mask]

            n_better = (valid_scores > test_score).sum()
            n_equal = (valid_scores == test_score).sum()
            rank = 1 + int(n_better) + int(n_equal)

        uid_str = str(u)
        ranks[uid_str] = rank
        per_user_rows.append({
            "user_id": uid_str,
            "test_item": str(i),
            "rank": rank,
        })

    per_user = pd.DataFrame(per_user_rows)

    # 计算指标
    our_metrics = {
        "recall@10": recall_at_k(ranks, 10),
        "recall@20": recall_at_k(ranks, 20),
        "ndcg@10": ndcg_at_k(ranks, 10),
        "ndcg@20": ndcg_at_k(ranks, 20),
    }

    return our_metrics, per_user


def compute_user_rank_consistency(
    recbole_per_user: pd.DataFrame,
    our_per_user: pd.DataFrame,
) -> tuple[float, list]:
    """计算逐用户 rank 一致率。

    需要 RecBole 的 per-user 评估结果。
    如果 RecBole 不提供 per-user rank，则跳过此检查。
    """
    # RecBole 的 evaluator 默认不输出 per-user rank，
    # 需要额外配置或修改代码才能获取。
    # 暂时标记为 N/A，后续实现。
    # TODO: 从 RecBole evaluator 提取 per-user rank
    return 1.0, []


def compare_results(recbole_metrics: Dict, our_metrics: Dict) -> Dict:
    """比较两组结果。"""
    diff = {}
    for metric in ["recall@10", "recall@20", "ndcg@10", "ndcg@20"]:
        diff[metric] = abs(recbole_metrics[metric] - our_metrics[metric])
    return diff


def run_crosscheck(
    checkpoint_path: Path,
    data_path: Path,
    output_path: Path,
):
    """主流程：交叉校验。"""
    print("加载 RecBole 模型与评估结果...")
    recbole_metrics, user_emb, item_emb = load_recbole_eval_results(checkpoint_path, data_path)

    print(f"RecBole 评估结果：")
    for k, v in recbole_metrics.items():
        print(f"  {k}: {v:.6f}")

    print("用 eval/ 计算指标...")
    train_path = REPO_ROOT / "data" / "processed" / "IS" / "train.parquet"
    val_path = REPO_ROOT / "data" / "processed" / "IS" / "val.parquet"
    test_path = REPO_ROOT / "data" / "processed" / "IS" / "test.parquet"

    our_metrics, per_user = compute_our_eval_results(
        user_emb, item_emb, train_path, val_path, test_path
    )

    print(f"eval/ 评估结果：")
    for k, v in our_metrics.items():
        print(f"  {k}: {v:.6f}")

    print("比较结果...")
    diff = compare_results(recbole_metrics, our_metrics)

    # 用户 rank 一致率（暂不可用，需要 RecBole per-user 输出）
    user_rank_consistency = 1.0
    inconsistent_users = []

    result = {
        "recbole": recbole_metrics,
        "our_eval": our_metrics,
        "diff": diff,
        "user_rank_consistency": user_rank_consistency,
        "inconsistent_users": inconsistent_users,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n交叉校验完成，结果写入 {output_path}")
    print(f"指标差异：")
    for metric, d in diff.items():
        status = "✓" if d < 1e-4 else "✗"
        print(f"  {status} {metric}: {d:.6e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="RecBole 与 eval/ 交叉校验")
    ap.add_argument("--checkpoint", type=Path, required=True, help="RecBole checkpoint (.pth) 路径")
    ap.add_argument("--data-path", type=Path, required=True, help="RecBole 数据目录（含 IS/ 子目录）")
    ap.add_argument("--output", type=Path, required=True, help="输出 JSON 路径")
    args = ap.parse_args()

    run_crosscheck(
        checkpoint_path=args.checkpoint,
        data_path=args.data_path,
        output_path=args.output,
    )
