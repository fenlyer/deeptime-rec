#!/usr/bin/env python3
"""
Amazon Review 数据预处理脚本
==============================
功能:
  1. 加载原始 JSON.gz 数据
  2. 数据清洗 (去重、过滤、时间戳处理)
  3. 构建用户-物品交互矩阵
  4. 生成训练/验证/测试划分
  5. 统计信息输出
  6. 导出为 CSV + Parquet 格式

用法:
  python prepare_data.py                          # 处理全部类别
  python prepare_data.py --categories IS           # 只处理主实验数据
  python prepare_data.py --k-core 5                # 使用 5-core 过滤
  python prepare_data.py --output-format csv       # 只输出 CSV
  python prepare_data.py --stats-only              # 只输出统计信息, 不处理
"""

import argparse
import gzip
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR / "raw"
PROCESSED_DIR = SCRIPT_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = {
    "IS": "Industrial_and_Scientific",
    "TH": "Tools_and_Home_Improvement",
    "OP": "Office_Products",
    "AJ": "Automotive",
}


def log(msg: str, level: str = "INFO"):
    prefix = {"INFO": "📊", "WARN": "⚠️", "ERROR": "❌", "OK": "✅"}.get(level, "ℹ️")
    print(f"{prefix} [{level}] {msg}")


def load_json_gz(filepath: Path) -> list[dict]:
    """加载 .json.gz 文件, 每行一个 JSON 对象"""
    records = []
    log(f"加载: {filepath.name}")

    open_fn = gzip.open if filepath.suffix == ".gz" else open
    with open_fn(filepath, "rt", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                if line_no <= 5:
                    log(f"跳过无效 JSON (行 {line_no})", "WARN")

    log(f"读取 {len(records):,} 条记录")
    return records


def load_reviews(filepath: Path) -> pd.DataFrame:
    """加载评论数据并转为 DataFrame"""
    records = load_json_gz(filepath)
    df = pd.DataFrame(records)

    # 统一字段名 (兼容 2018 和 2023 版本)
    rename_map = {
        "reviewerID": "user_id",
        "asin": "item_id",
        "overall": "rating",
        "unixReviewTime": "timestamp",
        "reviewText": "review_text",
        "summary": "summary",
        "verified": "verified",
        "reviewerName": "reviewer_name",
        "reviewTime": "review_time",
    }
    for old, new in rename_map.items():
        if old in df.columns:
            df = df.rename(columns={old: new})

    # 2023 版本字段映射
    if "rating" not in df.columns and "overall" in df.columns:
        df["rating"] = df["overall"]
    if "user_id" not in df.columns and "user_id" in df.columns:
        pass  # 已经是新名
    if "item_id" not in df.columns and "asin" in df.columns:
        df["item_id"] = df["asin"]
    if "timestamp" not in df.columns and "timestamp" in df.columns:
        pass

    # 确保关键列存在
    required_cols = ["user_id", "item_id", "rating", "timestamp"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        log(f"缺少关键列: {missing}, 可用列: {list(df.columns)}", "ERROR")
        return pd.DataFrame()

    return df[required_cols + [c for c in ["review_text", "summary", "verified"] if c in df.columns]]


def load_meta(filepath: Path) -> pd.DataFrame:
    """加载物品元数据并转为 DataFrame"""
    records = load_json_gz(filepath)
    df = pd.DataFrame(records)

    rename_map = {
        "asin": "item_id",
        "title": "title",
        "brand": "brand",
        "category": "category",
        "description": "description",
        "price": "price",
        "feature": "features",
    }
    for old, new in rename_map.items():
        if old in df.columns:
            df = df.rename(columns={old: new})

    keep_cols = [c for c in ["item_id", "title", "brand", "category", "description", "price", "features"] if c in df.columns]
    return df[keep_cols] if keep_cols else pd.DataFrame()


def filter_kcore(df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """K-core 过滤: 保留至少有 k 条交互的用户和物品"""
    log(f"K-core 过滤 (k={k})...")
    iteration = 0
    while True:
        iteration += 1
        user_counts = df["user_id"].value_counts()
        item_counts = df["item_id"].value_counts()

        valid_users = user_counts[user_counts >= k].index
        valid_items = item_counts[item_counts >= k].index

        filtered = df[df["user_id"].isin(valid_users) & df["item_id"].isin(valid_items)]

        if len(filtered) == len(df):
            log(f"K-core 收敛于第 {iteration} 轮")
            break

        reduction = len(df) - len(filtered)
        log(f"  轮次 {iteration}: {len(df):,} → {len(filtered):,} (减少 {reduction:,})")
        df = filtered

    return df


def encode_ids(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """将 user_id 和 item_id 编码为连续整数"""
    log("编码 ID 为连续整数...")

    user_set = sorted(df["user_id"].unique())
    item_set = sorted(df["item_id"].unique())

    user2idx = {uid: idx for idx, uid in enumerate(user_set)}
    item2idx = {iid: idx for idx, iid in enumerate(item_set)}

    df_encoded = df.copy()
    df_encoded["user_idx"] = df_encoded["user_id"].map(user2idx)
    df_encoded["item_idx"] = df_encoded["item_id"].map(item2idx)

    id_maps = {
        "user2idx": user2idx,
        "item2idx": item2idx,
        "idx2user": {v: k for k, v in user2idx.items()},
        "idx2item": {v: k for k, v in item2idx.items()},
    }

    log(f"用户: {len(user2idx):,}, 物品: {len(item2idx):,}")
    return df_encoded, id_maps


def temporal_split(df: pd.DataFrame, val_ratio: float = 0.1, test_ratio: float = 0.1) -> dict:
    """
    按时间戳划分训练/验证/测试集
    - 每个用户的交互按时间排序
    - 最后 test_ratio 作为测试
    - 倒数第二个 val_ratio 作为验证
    - 其余作为训练
    """
    log(f"时序划分 (val={val_ratio:.0%}, test={test_ratio:.0%})...")

    df_sorted = df.sort_values("timestamp")
    train_records, val_records, test_records = [], [], []

    for uid, group in df_sorted.groupby("user_id"):
        n = len(group)
        if n < 3:
            train_records.append(group)
            continue

        n_test = max(1, int(n * test_ratio))
        n_val = max(1, int(n * val_ratio))
        n_train = n - n_val - n_test

        if n_train < 1:
            train_records.append(group.iloc[:1])
            val_records.append(group.iloc[1:2])
            test_records.append(group.iloc[2:])
        else:
            train_records.append(group.iloc[:n_train])
            val_records.append(group.iloc[n_train:n_train + n_val])
            test_records.append(group.iloc[n_train + n_val:])

    result = {
        "train": pd.concat(train_records, ignore_index=True),
        "val": pd.concat(val_records, ignore_index=True) if val_records else pd.DataFrame(),
        "test": pd.concat(test_records, ignore_index=True) if test_records else pd.DataFrame(),
    }

    for split, data in result.items():
        log(f"  {split}: {len(data):,} 条 ({len(data)/len(df)*100:.1f}%)")

    return result


def compute_stats(df: pd.DataFrame, name: str = "") -> dict:
    """计算数据集统计信息"""
    stats = {
        "name": name,
        "num_interactions": len(df),
        "num_users": df["user_id"].nunique(),
        "num_items": df["item_id"].nunique(),
        "sparsity": 1 - len(df) / (df["user_id"].nunique() * df["item_id"].nunique()),
        "rating_mean": df["rating"].mean(),
        "rating_std": df["rating"].std(),
        "avg_interactions_per_user": len(df) / df["user_id"].nunique(),
        "avg_interactions_per_item": len(df) / df["item_id"].nunique(),
        "median_interactions_per_user": df["user_id"].value_counts().median(),
        "median_interactions_per_item": df["item_id"].value_counts().median(),
        "timestamp_min": df["timestamp"].min(),
        "timestamp_max": df["timestamp"].max(),
    }

    # 时间跨度
    if stats["timestamp_min"] and stats["timestamp_max"]:
        from datetime import datetime
        t_min = datetime.fromtimestamp(stats["timestamp_min"]).strftime("%Y-%m-%d")
        t_max = datetime.fromtimestamp(stats["timestamp_max"]).strftime("%Y-%m-%d")
        stats["time_range"] = f"{t_min} ~ {t_max}"

    return stats


def print_stats(stats: dict):
    """美观地打印统计信息"""
    print(f"\n{'='*55}")
    print(f"  📊 数据集统计: {stats['name']}")
    print(f"{'='*55}")
    print(f"  交互数:           {stats['num_interactions']:>12,}")
    print(f"  用户数:           {stats['num_users']:>12,}")
    print(f"  物品数:           {stats['num_items']:>12,}")
    print(f"  稀疏度:           {stats['sparsity']:>12.4%}")
    print(f"  评分均值/标准差:  {stats['rating_mean']:.2f} ± {stats['rating_std']:.2f}")
    print(f"  人均交互 (均值):  {stats['avg_interactions_per_user']:>12.2f}")
    print(f"  人均交互 (中位数):{stats['median_interactions_per_user']:>12.1f}")
    print(f"  物品均交互 (均值):{stats['avg_interactions_per_item']:>12.2f}")
    print(f"  时间跨度:         {stats.get('time_range', 'N/A')}")
    print(f"{'='*55}\n")


def process_category(short_name: str, k_core: int = 0, output_format: str = "both",
                     stats_only: bool = False, val_ratio: float = 0.1, test_ratio: float = 0.1):
    """处理单个类别的数据"""
    full_name = CATEGORIES[short_name]
    log(f"处理 [{short_name}] {full_name}")
    log(f"{'='*50}")

    # 查找原始数据文件
    review_file = None
    meta_file = None
    for f in RAW_DIR.glob(f"*{full_name}*"):
        if f.name.startswith("meta_"):
            meta_file = f
        else:
            review_file = f

    if review_file is None:
        log(f"未找到评论数据: *{full_name}*", "ERROR")
        log(f"请先运行 download_data.py 下载数据", "ERROR")
        return None

    # 加载评论数据
    df = load_reviews(review_file)
    if df.empty:
        log("评论数据为空, 跳过", "ERROR")
        return None

    # 加载元数据 (如果有)
    meta_df = None
    if meta_file and meta_file.exists():
        meta_df = load_meta(meta_file)

    # K-core 过滤
    if k_core > 0:
        df = filter_kcore(df, k=k_core)

    # 计算并打印统计
    stats = compute_stats(df, name=f"{short_name}-{full_name}")
    print_stats(stats)

    if stats_only:
        return stats

    # ID 编码
    df_encoded, id_maps = encode_ids(df)

    # 时序划分
    splits = temporal_split(df_encoded, val_ratio=val_ratio, test_ratio=test_ratio)

    # 输出目录
    out_dir = PROCESSED_DIR / short_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # 保存数据
    save_formats = []
    if output_format in ("csv", "both"):
        save_formats.append("csv")
    if output_format in ("parquet", "both"):
        save_formats.append("parquet")

    for split_name, split_df in splits.items():
        for fmt in save_formats:
            if fmt == "csv":
                path = out_dir / f"{split_name}.csv"
                split_df.to_csv(path, index=False)
            elif fmt == "parquet":
                path = out_dir / f"{split_name}.parquet"
                split_df.to_parquet(path, index=False)
            log(f"保存 {split_name}: {path.name}")

    # 保存 ID 映射
    id_dir = out_dir / "id_maps"
    id_dir.mkdir(exist_ok=True)
    with open(id_dir / "user2idx.json", "w") as f:
        json.dump(id_maps["user2idx"], f, indent=2)
    with open(id_dir / "item2idx.json", "w") as f:
        json.dump(id_maps["item2idx"], f, indent=2)

    # 保存元数据
    if meta_df is not None and not meta_df.empty:
        for fmt in save_formats:
            if fmt == "csv":
                meta_df.to_csv(out_dir / "item_meta.csv", index=False)
            elif fmt == "parquet":
                meta_df.to_parquet(out_dir / "item_meta.parquet", index=False)
        log(f"保存物品元数据: item_meta.*")

    # 保存统计信息
    with open(out_dir / "stats.json", "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False, default=str)

    log(f"处理完成: {out_dir}", "OK")
    return stats


def generate_cross_domain_data(stats_list: list[dict]):
    """生成跨域数据的汇总统计和共享用户/物品分析"""
    log("生成跨域分析...")

    summary_dir = PROCESSED_DIR / "cross_domain"
    summary_dir.mkdir(exist_ok=True)

    # 汇总统计
    summary = {
        "datasets": stats_list,
        "total_interactions": sum(s.get("num_interactions", 0) for s in stats_list if s),
        "total_users": sum(s.get("num_users", 0) for s in stats_list if s),
        "total_items": sum(s.get("num_items", 0) for s in stats_list if s),
    }

    with open(summary_dir / "cross_domain_summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    # 打印跨域汇总表
    print(f"\n{'='*70}")
    print(f"  📊 跨域数据汇总")
    print(f"{'='*70}")
    print(f"{'数据集':<8} {'用户数':>10} {'物品数':>10} {'交互数':>12} {'稀疏度':>10}")
    print("-" * 55)
    for s in stats_list:
        if s:
            print(f"[{s['name'][:6]}] {s['num_users']:>8,} {s['num_items']:>10,} {s['num_interactions']:>12,} {s['sparsity']:>9.4%}")
    print("-" * 55)
    print(f"{'合计':>8} {summary['total_users']:>8,} {summary['total_items']:>10,} {summary['total_interactions']:>12,}")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Amazon Review 数据预处理")
    parser.add_argument("--categories", nargs="+", choices=list(CATEGORIES.keys()),
                        default=list(CATEGORIES.keys()),
                        help="要处理的类别")
    parser.add_argument("--k-core", type=int, default=0,
                        help="K-core 过滤阈值, 0=不过滤 (推荐 5)")
    parser.add_argument("--output-format", choices=["csv", "parquet", "both"], default="both",
                        help="输出格式")
    parser.add_argument("--stats-only", action="store_true",
                        help="只输出统计信息, 不生成训练数据")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="验证集比例")
    parser.add_argument("--test-ratio", type=float, default=0.1, help="测试集比例")
    args = parser.parse_args()

    log("Amazon Review 数据预处理器")
    log(f"原始数据: {RAW_DIR}")
    log(f"输出目录: {PROCESSED_DIR}")
    log(f"K-core: {args.k_core}")
    log(f"类别: {', '.join(args.categories)}")
    print()

    all_stats = []
    for short_name in args.categories:
        stats = process_category(
            short_name,
            k_core=args.k_core,
            output_format=args.output_format,
            stats_only=args.stats_only,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
        )
        all_stats.append(stats)

    if not args.stats_only:
        generate_cross_domain_data(all_stats)

    log("全部处理完成!", "OK")


if __name__ == "__main__":
    main()
