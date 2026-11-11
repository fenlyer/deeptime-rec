#!/usr/bin/env python3
"""
数据集统计脚本

输出 Amazon 2023 (IS/TH/OP) 和 AJ (Alibaba IJCAI15) 的实测统计：
- 用户数、商品数、交互数
- 稀疏度、平均交互/用户
- 时间跨度
- 行为分布（buy/collect/click/show）
- 最小用户交互、最小商品交互
- 重复对数

用法：
  python3 data/compute_dataset_stats.py
"""

import csv
import gzip
from collections import Counter
from datetime import datetime
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent
RAW_2023 = DATA_ROOT / "raw_2023"
RAW_AJ = DATA_ROOT / "raw_aj" / "data_format1"


def count_amazon_5core(filepath: Path, name: str) -> dict:
    """统计 Amazon 5-core 评分文件"""
    uc, ic, rated = Counter(), Counter(), Counter()
    n = 0
    ts_min = ts_max = None
    pairs = set()
    dup = 0

    with gzip.open(filepath, "rt") as fh:
        reader = csv.reader(fh)
        next(reader)  # skip header
        for row in reader:
            if len(row) < 4:
                continue
            user_id, parent_asin = row[0], row[1]
            rating = int(float(row[2]))
            timestamp = int(row[3])

            k = (user_id, parent_asin)
            if k in pairs:
                dup += 1
            else:
                pairs.add(k)

            uc[user_id] += 1
            ic[parent_asin] += 1
            rated[rating] += 1
            n += 1
            ts_min = timestamp if ts_min is None else min(ts_min, timestamp)
            ts_max = timestamp if ts_max is None else max(ts_max, timestamp)

    # 行为推导
    buy = rated[5]
    collect = rated[4]
    click = rated[3]
    show = rated[1] + rated[2]
    sparsity = 1 - n / (len(uc) * len(ic))

    time_span_start = datetime.fromtimestamp(ts_min / 1000).strftime("%Y-%m")
    time_span_end = datetime.fromtimestamp(ts_max / 1000).strftime("%Y-%m")

    return {
        "name": name,
        "users": len(uc),
        "items": len(ic),
        "interactions": n,
        "unique_pairs": len(pairs),
        "duplicate_pairs": dup,
        "sparsity": sparsity * 100,
        "avg_interactions_per_user": n / len(uc),
        "min_user_interactions": min(uc.values()) if uc else 0,
        "min_item_interactions": min(ic.values()) if ic else 0,
        "time_span": f"{time_span_start} ~ {time_span_end}",
        "buy": buy,
        "collect": collect,
        "click": click,
        "show": show,
        "buy_pct": buy / n * 100,
        "collect_pct": collect / n * 100,
        "click_pct": click / n * 100,
        "show_pct": show / n * 100,
    }


def count_aj_user_log(filepath: Path, name: str = "AJ") -> dict:
    """统计 AJ 天猫用户行为日志"""
    uc, ic = Counter(), Counter()
    action_counts = Counter()
    n = 0
    ts_min = ts_max = None
    pairs = set()
    dup = 0

    with open(filepath, "r") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            user_id = row["user_id"]
            item_id = row["item_id"]
            action_type = row["action_type"]
            timestamp = row["time_stamp"]

            k = (user_id, item_id)
            if k in pairs:
                dup += 1
            else:
                pairs.add(k)

            uc[user_id] += 1
            ic[item_id] += 1
            action_counts[action_type] += 1
            n += 1

            # AJ 时间戳格式：MMDD (如 0829)
            if ts_min is None:
                ts_min = timestamp
            ts_max = timestamp

    sparsity = 1 - n / (len(uc) * len(ic)) if len(uc) > 0 and len(ic) > 0 else 0

    return {
        "name": name,
        "users": len(uc),
        "items": len(ic),
        "interactions": n,
        "unique_pairs": len(pairs),
        "duplicate_pairs": dup,
        "sparsity": sparsity * 100,
        "avg_interactions_per_user": n / len(uc) if uc else 0,
        "min_user_interactions": min(uc.values()) if uc else 0,
        "min_item_interactions": min(ic.values()) if ic else 0,
        "time_span": "N/A (MMDD format)",
        "action_distribution": dict(action_counts),
    }


def print_amazon_stats(stats: dict):
    """格式化打印 Amazon 统计"""
    print(f"\n{'=' * 70}")
    print(f"  {stats['name']}")
    print(f"{'=' * 70}")
    print(f"  用户数        : {stats['users']:>12,}")
    print(f"  商品数        : {stats['items']:>12,}")
    print(f"  交互数        : {stats['interactions']:>12,}")
    print(f"  唯一对数      : {stats['unique_pairs']:>12,}")
    print(f"  重复对数      : {stats['duplicate_pairs']:>12}")
    print(f"  稀疏度        : {stats['sparsity']:>11.4f}%")
    print(f"  平均交互/用户 : {stats['avg_interactions_per_user']:>11.2f}")
    print(f"  最小用户交互  : {stats['min_user_interactions']:>12}")
    print(f"  最小商品交互  : {stats['min_item_interactions']:>12}")
    print(f"  时间跨度      : {stats['time_span']}")
    print(f"\n  行为分布：")
    print(f"    buy   (rating=5) : {stats['buy']:>12,} ({stats['buy_pct']:.1f}%)")
    print(f"    collect (rating=4): {stats['collect']:>12,} ({stats['collect_pct']:.1f}%)")
    print(f"    click (rating=3) : {stats['click']:>12,} ({stats['click_pct']:.1f}%)")
    print(f"    show (rating=1/2): {stats['show']:>12,} ({stats['show_pct']:.1f}%)")


def print_aj_stats(stats: dict):
    """格式化打印 AJ 统计"""
    print(f"\n{'=' * 70}")
    print(f"  {stats['name']}")
    print(f"{'=' * 70}")
    print(f"  用户数        : {stats['users']:>12,}")
    print(f"  商品数        : {stats['items']:>12,}")
    print(f"  交互数        : {stats['interactions']:>12,}")
    print(f"  唯一对数      : {stats['unique_pairs']:>12,}")
    print(f"  重复对数      : {stats['duplicate_pairs']:>12}")
    print(f"  稀疏度        : {stats['sparsity']:>11.4f}%")
    print(f"  平均交互/用户 : {stats['avg_interactions_per_user']:>11.2f}")
    print(f"  最小用户交互  : {stats['min_user_interactions']:>12}")
    print(f"  最小商品交互  : {stats['min_item_interactions']:>12}")
    print(f"\n  行为分布（action_type）：")
    for action, count in sorted(stats["action_distribution"].items()):
        pct = count / stats["interactions"] * 100
        print(f"    action_type={action}: {count:>12,} ({pct:.1f}%)")


def main():
    print("=" * 70)
    print("  数据集统计脚本")
    print("  输出实测数据，暂不回填到论文")
    print("=" * 70)

    # Amazon 2023 数据集
    amazon_datasets = [
        (RAW_2023 / "IS_5core.csv.gz", "Industrial & Scientific (IS)"),
        (RAW_2023 / "TH_5core.csv.gz", "Tools & Home Improvement (TH)"),
        (RAW_2023 / "OP_5core.csv.gz", "Office Products (OP)"),
    ]

    amazon_stats = []
    for filepath, name in amazon_datasets:
        if filepath.exists():
            stats = count_amazon_5core(filepath, name)
            amazon_stats.append(stats)
            print_amazon_stats(stats)
        else:
            print(f"\n⚠ {name}: 文件不存在 {filepath}")

    # AJ 数据集
    aj_file = RAW_AJ / "user_log_format1.csv"
    if aj_file.exists():
        aj_stats = count_aj_user_log(aj_file)
        print_aj_stats(aj_stats)
    else:
        print(f"\n⚠ AJ: 文件不存在 {aj_file}")

    print(f"\n{'=' * 70}")
    print("  统计完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
