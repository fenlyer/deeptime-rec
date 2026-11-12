#!/usr/bin/env python3
"""
论文表 5-1「实验数据集统计信息」复现脚本
==========================================
从 processed/{name}/ 的划分文件与 stats.json 重算表 5-1 的每一列，
输出可直接粘贴进论文的表格，并做一次「重算值 ↔ stats.json」的自校验。

口径：
    - 用户数 / 商品数 / 交互数：按 train+val+test 合并后的 (user_id, item_id) 唯一对统计，
      与 prepare_data.py 的 compute_stats 一致；AJ 另列行为记录数（|A| ≠ |E|）
    - 稀疏度 = 1 − |E| / (|U|·|I|)，保留 4 位小数（表 5-1 用百分数）
    - 平均交互/用户 = |E| / |U|，保留 2 位
    - 时间跨度取 timestamp 最小/最大，按月格式化为 YYYY-MM

用法：
    python data/verify_5_1_data.py            # 四数据集，打印表 5-1
    python data/verify_5_1_data.py --check    # 额外做 stats.json 一致性校验
    python data/verify_5_1_data.py --markdown # 输出 Markdown 表格

与相邻脚本的分工：
    prepare_data.py          产出 processed/（唯一写入口）
    verify_4_1_data.py       4.1 节的规模/长尾/λ 核验（含跨数据集对比）
    verify_5_6_cold_start.py 5.6 节冷启动分层
    本脚本                    仅负责表 5-1 这一张表的完整复现，不重复上面两者的细分项
"""

import argparse
import json
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = SCRIPT_DIR / "processed"

# 表 5-1 的行顺序与显示名
DATASETS = [
    ("IS", "Industrial & Scientific (IS)"),
    ("TH", "Tools & Home Improvement (TH)"),
    ("OP", "Office Products (OP)"),
    ("AJ", "Alibaba IJCAI15 (AJ)"),
]


def load_pairs(name: str) -> pd.DataFrame:
    """
    合并三个划分并去重到 (user_id, item_id) 对。

    AJ 同一对可有多条 action_type 记录，按行计数会把行为记录数误当成交互对数，
    因此交互数一律以去重后的对数计；行为记录数在 stats.json 的
    num_behavior_records 中单独取。
    """
    frames = [pd.read_csv(PROCESSED_DIR / name / f"{s}.csv",
                          usecols=["user_id", "item_id", "timestamp"])
              for s in ("train", "val", "test")]
    return pd.concat(frames, ignore_index=True).drop_duplicates(["user_id", "item_id"])


def table_row(name: str, display: str) -> dict:
    """
    重算一个数据集的表 5-1 全部列。

    返回 dict，键与表头一致；数值字段保留原始精度，格式化在打印阶段做，
    便于 --check 时与 stats.json 直接比对。
    """
    pairs = load_pairs(name)
    n_users = int(pairs["user_id"].nunique())
    n_items = int(pairs["item_id"].nunique())
    n_pairs = int(len(pairs))
    t_min, t_max = int(pairs["timestamp"].min()), int(pairs["timestamp"].max())

    stats = json.loads((PROCESSED_DIR / name / "stats.json").read_text())
    return {
        "数据集": display,
        "用户数": n_users,
        "商品数": n_items,
        "交互数": n_pairs,
        "行为记录数": int(stats["num_behavior_records"]),
        "稀疏度": f"{1 - n_pairs / (n_users * n_items):.4%}",
        "平均交互/用户": f"{n_pairs / n_users:.2f}",
        "时间跨度": (f"{pd.to_datetime(t_min, unit='s'):%Y-%m}"
                     f" ~ {pd.to_datetime(t_max, unit='s'):%Y-%m}"),
    }


def check_against_stats(rows: list[dict]) -> bool:
    """
    将重算值与 stats.json 逐项比对，返回是否全部一致。

    stats.json 由 prepare_data.py 在同一次运行中写入，若此处不一致，
    说明 processed/ 下的划分文件与统计文件来自不同版本，需重跑预处理。
    """
    print("\n" + "=" * 78)
    print("自校验：重算值 ↔ stats.json")
    print("=" * 78)
    ok_all = True
    for (name, _), row in zip(DATASETS, rows):
        stats = json.loads((PROCESSED_DIR / name / "stats.json").read_text())
        pairs = {
            "用户数": (row["用户数"], stats["num_users"]),
            "商品数": (row["商品数"], stats["num_items"]),
            "交互数": (row["交互数"], stats["num_pairs"]),
        }
        for label, (got, want) in pairs.items():
            ok = got == want
            ok_all &= ok
            mark = "✅" if ok else "❌"
            print(f"  {mark} {name} {label}: 重算 {got:,} / stats {want:,}")
    return ok_all


def print_table(rows: list[dict], markdown: bool) -> None:
    """按 Markdown 或等宽文本打印表 5-1。"""
    cols = ["数据集", "用户数", "商品数", "交互数", "稀疏度", "平均交互/用户", "时间跨度"]
    if markdown:
        print("| " + " | ".join(cols) + " |")
        print("|" + "---|" * len(cols))
        for r in rows:
            print("| " + " | ".join(
                f"{r[c]:,}" if c in ("用户数", "商品数", "交互数") else str(r[c])
                for c in cols) + " |")
    else:
        df = pd.DataFrame(rows)[cols]
        for c in ("用户数", "商品数", "交互数"):
            df[c] = df[c].map(lambda x: f"{x:,}")
        print(df.to_string(index=False))


def main() -> None:
    ap = argparse.ArgumentParser(description="论文表 5-1 数据集统计复现")
    ap.add_argument("--check", action="store_true", help="与 stats.json 交叉校验")
    ap.add_argument("--markdown", action="store_true", help="输出 Markdown 表格")
    args = ap.parse_args()

    rows = [table_row(n, d) for n, d in DATASETS]

    print("=" * 78)
    print("表5-1  实验数据集统计信息（5-core 过滤后）")
    print("=" * 78)
    print_table(rows, args.markdown)

    # AJ 的行为记录数 > 交互对数，单独说明，避免读者误以为统计口径不一致
    aj = next(r for r in rows if "AJ" in r["数据集"])
    if aj["行为记录数"] != aj["交互数"]:
        print(f"\n注：AJ 行为记录数 {aj['行为记录数']:,} > 交互对数 {aj['交互数']:,}，"
              "因同一用户-物品对可含多条原生 action_type 事件；"
              "IS/TH/OP 每个对仅一条评分，故两者相等。")

    if args.check:
        ok = check_against_stats(rows)
        print(f"\n{'✅ 全部一致' if ok else '❌ 存在不一致，需重跑 prepare_data.py'}")


if __name__ == "__main__":
    main()
