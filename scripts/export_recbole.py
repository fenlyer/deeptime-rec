"""导出 RecBole atomic 文件（S1-b）

把 data/processed/IS 的 train/val/test 转成 RecBole 能读取的 .inter 文件，
使用 benchmark_filename 方式加载冻结切分。

口径
----
    - AJ 聚合：按 (user, item) 对聚合（同一对可能有多条行为记录）
        - timestamp 取最新（max）
        - rating 取最高（max，因为 rating 是正向反馈强度）
    - 字段：user_id:token, item_id:token, rating:float, timestamp:float
    - 用户/物品 ID 用 user_idx/item_idx（已在 processed/ 中映射好）

输出
----
    data/recbole/IS/
        IS.train.inter
        IS.val.inter
        IS.test.inter

使用
----
    python scripts/export_recbole.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "processed" / "IS"
OUT_DIR = REPO_ROOT / "data" / "recbole" / "IS"


def aggregate_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """按 (user, item) 对聚合，取最新 timestamp 和最高 rating。

    参数
    ----
    df : DataFrame，列 user_idx, item_idx, timestamp, rating

    返回
    ----
    DataFrame，列 user_idx, item_idx, timestamp, rating
    每 (user, item) 对一行。
    """
    grouped = df.groupby(["user_idx", "item_idx"]).agg({
        "timestamp": "max",  # 取最新时间
        "rating": "max",     # 取最高评分
    }).reset_index()
    return grouped


def export_split(df: pd.DataFrame, split_name: str, out_dir: Path) -> Path:
    """导出单个 split 的 .inter 文件。

    参数
    ----
    df : DataFrame，列 user_idx, item_idx, timestamp, rating
    split_name : "train" / "val" / "test"
    out_dir : 输出目录

    返回
    ----
    输出文件路径
    """
    # AJ 聚合
    aggregated = aggregate_pairs(df)

    # 转成 RecBole atomic 格式
    # 列名：user_id:token, item_id:token, rating:float, timestamp:float
    recbole_df = pd.DataFrame({
        "user_id:token": aggregated["user_idx"].astype(str),
        "item_id:token": aggregated["item_idx"].astype(str),
        "rating:float": aggregated["rating"].astype(float),
        "timestamp:float": aggregated["timestamp"].astype(float),
    })

    out_path = out_dir / f"IS.{split_name}.inter"
    out_dir.mkdir(parents=True, exist_ok=True)
    recbole_df.to_csv(out_path, sep="\t", index=False)

    return out_path


def export_all():
    """导出全部三个 split。"""
    print("加载 processed/IS 数据...")
    train = pd.read_parquet(DATA_DIR / "train.parquet")
    val = pd.read_parquet(DATA_DIR / "val.parquet")
    test = pd.read_parquet(DATA_DIR / "test.parquet")

    print(f"原始数据：train={len(train)}, val={len(val)}, test={len(test)}")

    # 导出
    train_path = export_split(train, "train", OUT_DIR)
    val_path = export_split(val, "val", OUT_DIR)
    test_path = export_split(test, "test", OUT_DIR)

    # 统计
    train_agg = aggregate_pairs(train)
    val_agg = aggregate_pairs(val)
    test_agg = aggregate_pairs(test)

    print(f"导出完成（AJ 聚合后）：")
    print(f"  {train_path.name}: {len(train_agg)} 行")
    print(f"  {val_path.name}: {len(val_agg)} 行")
    print(f"  {test_path.name}: {len(test_agg)} 行")

    # 验证用户/物品集合一致性
    proc_users = set(
        pd.concat([train["user_idx"], val["user_idx"], test["user_idx"]]).unique()
    )
    proc_items = set(
        pd.concat([train["item_idx"], val["item_idx"], test["item_idx"]]).unique()
    )

    inter_train = pd.read_csv(train_path, sep="\t")
    inter_val = pd.read_csv(val_path, sep="\t")
    inter_test = pd.read_csv(test_path, sep="\t")

    inter_users = set(
        pd.concat([
            inter_train["user_id:token"],
            inter_val["user_id:token"],
            inter_test["user_id:token"],
        ]).unique()
    )
    inter_users = {int(u) for u in inter_users}

    inter_items = set(
        pd.concat([
            inter_train["item_id:token"],
            inter_val["item_id:token"],
            inter_test["item_id:token"],
        ]).unique()
    )
    inter_items = {int(i) for i in inter_items}

    assert proc_users == inter_users, "用户集合不一致"
    assert proc_items == inter_items, "物品集合不一致"
    print(f"用户/物品集合一致性校验通过：{len(proc_users)} 用户, {len(proc_items)} 物品")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="导出 RecBole atomic 文件")
    ap.parse_args()
    export_all()
