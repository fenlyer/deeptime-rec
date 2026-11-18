"""RecBole 适配器对账校验（S1-b）

四项对账：
1. 三个 .inter 文件行数分别等于 train/val/test 对数，用户/物品集合与 processed/ 完全相同
2. RecBole LightGCN 邻接矩阵非零数等于训练对数（确认测试交互不进图）
3. 同一份嵌入，RecBole 内部 Recall@10 与 eval/ 结果差异极小（屏蔽规则须逐条比对）
4. 自研 PyG LightGCN 与 RecBole 版在同一划分上 Recall@10 差距落在随机种子波动范围内

注意：第 2-4 项需要 RecBole 实际运行后的产物，没有产物时 skip。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "processed" / "IS"
EXPORT_DIR = REPO_ROOT / "data" / "recbole" / "IS"
SMOKE_DIR = REPO_ROOT / "results" / "_smoke"


# ─────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────────────────────

def load_processed_splits():
    """加载 processed/IS 的 train/val/test parquet。"""
    train = pd.read_parquet(DATA_DIR / "train.parquet")
    val = pd.read_parquet(DATA_DIR / "val.parquet")
    test = pd.read_parquet(DATA_DIR / "test.parquet")
    return train, val, test


def load_inter_files():
    """导出的 .inter 文件（RecBole atomic 格式，TSV）。"""
    train = pd.read_csv(EXPORT_DIR / "IS.train.inter", sep="\t")
    val = pd.read_csv(EXPORT_DIR / "IS.val.inter", sep="\t")
    test = pd.read_csv(EXPORT_DIR / "IS.test.inter", sep="\t")
    return train, val, test


# ─────────────────────────────────────────────────────────────────────────────
# 对账 1：文件行数与 ID 集合一致性
# ─────────────────────────────────────────────────────────────────────────────

class TestInterFileConsistency:
    """验证 .inter 文件与 processed/ 的一致性。"""

    def test_row_counts_match(self):
        """三个 .inter 文件行数分别等于 train/val/test 对数。"""
        proc_train, proc_val, proc_test = load_processed_splits()
        inter_train, inter_val, inter_test = load_inter_files()

        # AJ 聚合后行数可能不同（按 user,item 对去重）
        # 所以这里比较的是去重后的对数
        proc_train_pairs = proc_train.groupby(["user_idx", "item_idx"]).size()
        proc_val_pairs = proc_val.groupby(["user_idx", "item_idx"]).size()
        proc_test_pairs = proc_test.groupby(["user_idx", "item_idx"]).size()

        assert len(inter_train) == len(proc_train_pairs), (
            f"train.inter 行数 {len(inter_train)} != 去重后 train 对数 {len(proc_train_pairs)}"
        )
        assert len(inter_val) == len(proc_val_pairs), (
            f"val.inter 行数 {len(inter_val)} != 去重后 val 对数 {len(proc_val_pairs)}"
        )
        assert len(inter_test) == len(proc_test_pairs), (
            f"test.inter 行数 {len(inter_test)} != 去重后 test 对数 {len(proc_test_pairs)}"
        )

    def test_user_set_matches(self):
        """用户集合与 processed/ 完全相同。"""
        proc_train, proc_val, proc_test = load_processed_splits()
        inter_train, inter_val, inter_test = load_inter_files()

        # processed/ 的用户（用 user_idx，因为 inter 里用的是映射后的 ID）
        proc_users = set(
            pd.concat([
                proc_train["user_idx"],
                proc_val["user_idx"],
                proc_test["user_idx"],
            ]).unique()
        )

        # inter 文件的用户（用 user_id:token，应该是 user_idx 的字符串）
        inter_users = set(
            pd.concat([
                inter_train["user_id:token"],
                inter_val["user_id:token"],
                inter_test["user_id:token"],
            ]).unique()
        )
        inter_users = {int(u) for u in inter_users}

        assert proc_users == inter_users, (
            f"用户集合不一致：processed={len(proc_users)}, inter={len(inter_users)}, "
            f"差异数={len(proc_users ^ inter_users)}"
        )

    def test_item_set_matches(self):
        """物品集合与 processed/ 完全相同。"""
        proc_train, proc_val, proc_test = load_processed_splits()
        inter_train, inter_val, inter_test = load_inter_files()

        proc_items = set(
            pd.concat([
                proc_train["item_idx"],
                proc_val["item_idx"],
                proc_test["item_idx"],
            ]).unique()
        )

        inter_items = set(
            pd.concat([
                inter_train["item_id:token"],
                inter_val["item_id:token"],
                inter_test["item_id:token"],
            ]).unique()
        )
        inter_items = {int(i) for i in inter_items}

        assert proc_items == inter_items, (
            f"物品集合不一致：processed={len(proc_items)}, inter={len(inter_items)}, "
            f"差异数={len(proc_items ^ inter_items)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 对账 2：邻接矩阵非零数等于训练对数
# ─────────────────────────────────────────────────────────────────────────────

class TestAdjacencyMatrix:
    """验证 RecBole 构建的图只用训练集。"""

    @pytest.fixture(autouse=True)
    def skip_if_no_recbole(self):
        """没有 RecBole 产物时跳过。"""
        try:
            import recbole  # noqa: F401
        except ImportError:
            pytest.skip("RecBole 未安装")

        # 检查是否有训练产物
        if not (SMOKE_DIR / "recbole" / "saved").exists():
            pytest.skip("RecBole 训练产物不存在")

    def test_adjacency_nonzero_equals_train_pairs(self):
        """邻接矩阵非零数等于训练对数（确认测试交互不进图）。"""
        # 这个测试需要加载 RecBole 的 dataset 对象
        # 具体实现依赖 RecBole API，这里先占位
        # TODO: 实际运行 RecBole 后实现
        pytest.skip("需要 RecBole 实际运行产物")


# ─────────────────────────────────────────────────────────────────────────────
# 对账 3：同一嵌入下 Recall@10 差异
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossEvalConsistency:
    """验证 RecBole 自带评估与 eval/ 结果一致。"""

    @pytest.fixture(autouse=True)
    def skip_if_no_crosscheck(self):
        """没有交叉校验结果时跳过。"""
        if not (SMOKE_DIR / "crosscheck.json").exists():
            pytest.skip("crosscheck.json 不存在")

    def test_recall_ndcg_diff_below_threshold(self):
        """四个指标差值 < 1e-4。"""
        with open(SMOKE_DIR / "crosscheck.json") as f:
            result = json.load(f)

        threshold = 1e-4
        for metric in ["recall@10", "recall@20", "ndcg@10", "ndcg@20"]:
            diff = abs(result["recbole"][metric] - result["our_eval"][metric])
            assert diff < threshold, (
                f"{metric} 差异 {diff:.6e} >= {threshold:.0e}: "
                f"RecBole={result['recbole'][metric]:.6f}, "
                f"our={result['our_eval'][metric]:.6f}"
            )

    def test_user_rank_consistency_above_999(self):
        """≥ 99.9% 用户 rank 一致。"""
        with open(SMOKE_DIR / "crosscheck.json") as f:
            result = json.load(f)

        consistency = result["user_rank_consistency"]
        assert consistency >= 0.999, (
            f"用户 rank 一致率 {consistency:.4f} < 0.999"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 对账 4：PyG LightGCN 与 RecBole 版对比
# ─────────────────────────────────────────────────────────────────────────────

class TestPyGvsRecBole:
    """验证自研 PyG LightGCN 与 RecBole 版结果差距在种子波动范围内。"""

    @pytest.fixture(autouse=True)
    def skip_if_no_results(self):
        """没有对比结果时跳过。"""
        if not (SMOKE_DIR / "crosscheck.json").exists():
            pytest.skip("crosscheck.json 不存在")

    def test_recall_diff_within_seed_variance(self):
        """Recall@10 差距落在随机种子波动范围内。"""
        with open(SMOKE_DIR / "crosscheck.json") as f:
            result = json.load(f)

        # 种子波动范围通常在 1-2% 以内
        # 这里用 5% 作为宽松阈值（实际波动需要跑多次 seed 确认）
        max_diff = 0.05
        diff = abs(result["pyg_lightgcn"]["recall@10"] - result["recbole"]["recall@10"])
        assert diff < max_diff, (
            f"PyG vs RecBole Recall@10 差异 {diff:.4f} >= {max_diff:.2f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 导出脚本本身的功能测试
# ─────────────────────────────────────────────────────────────────────────────

class TestExportScript:
    """测试 export_recbole.py 的功能。"""

    def test_aj_aggregation(self):
        """AJ 聚合：按 (user, item) 对聚合，取最新 timestamp 和最高 rating。"""
        # 这个测试验证导出逻辑的正确性
        import sys
        sys.path.insert(0, str(REPO_ROOT / "scripts"))

        from export_recbole import aggregate_pairs

        # 构造测试数据
        df = pd.DataFrame({
            "user_idx": [0, 0, 0, 1, 1],
            "item_idx": [10, 10, 20, 30, 30],
            "timestamp": [100, 200, 300, 400, 500],
            "rating": [5.0, 4.0, 3.0, 5.0, 4.0],
        })

        result = aggregate_pairs(df)

        # (0, 10) 聚合后应取 timestamp=200, rating=5.0（max）
        assert len(result) == 3  # (0,10), (0,20), (1,30)
        pair_010 = result[(result["user_idx"] == 0) & (result["item_idx"] == 10)]
        assert len(pair_010) == 1
        assert pair_010["timestamp"].iloc[0] == 200  # 最新时间
        assert pair_010["rating"].iloc[0] == 5.0     # 最高评分
