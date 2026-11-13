#!/usr/bin/env python3
"""
论文 4.1 节数据口径核验脚本
============================
把 4.1 节正文里每一个可量化断言，回溯到 `processed/` 的实际数据，逐条打印核对结果。

口径：
    - 规模/稀疏度/长尾：按 (user_id, item_id) 唯一对统计，与表 5-1 一致
    - 式(4-1) 边权重：w = α_r · exp(-λ·(T_now−t)/T)，T=86400，T_now 取数据集最大时间戳
    - λ 对比取 0.1 / 0.01 / 0.001 三档，用于说明 4.1.2 与 5.8.1 的取值依据
    - 评分→反馈强度权重：5→3.0、4→1.5、3→1.0、1~2→0.1（表 4-1）

用法：
    python data/verify_4_1_data.py              # 默认 IS（主实验）
    python data/verify_4_1_data.py IS TH OP AJ  # 多数据集
    python data/verify_4_1_data.py IS --section lambda   # 只看 λ 敏感性

与相邻脚本的分工：
    prepare_data.py  产出 processed/（唯一入口，本脚本只读不写）
    本脚本           只做「论文数字 ↔ 数据」的一致性核对，不修改任何产物
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = SCRIPT_DIR / "processed"

SECONDS_PER_DAY = 86400
# 表 4-1：评分 → 反馈强度权重
RATING_ALPHA = {5: 3.0, 4: 1.5, 3: 1.0, 2: 0.1, 1: 0.1}
# 4.1.4 长尾阈值：交互次数 < 10 记为长尾商品
TAIL_DEG = 10


# =====================================================================
# 一、加载
# =====================================================================


def load_pairs(name: str) -> pd.DataFrame:
    """
    读取 train/val/test 并去重到 (user_id, item_id) 对。

    必须以「对」为单位统计：AJ 同一对有多条行为记录，按行计数会把
    行为记录数误当成交互对数，导致稀疏度与人均交互偏高。
    AJ 无 rating 字段（原生 action_type 已在预处理折算为 alpha），
    因此 rating 按存在与否动态取列，其余口径不受影响。
    """
    base = ["user_id", "item_id", "timestamp"]
    probe = pd.read_csv(PROCESSED_DIR / name / "train.csv", nrows=0)
    usecols = base + (["rating"] if "rating" in probe.columns else [])

    frames = [pd.read_csv(PROCESSED_DIR / name / f"{s}.csv", usecols=usecols)
              for s in ("train", "val", "test")]
    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates(["user_id", "item_id"])


# =====================================================================
# 二、各小节核验
# =====================================================================


def check_scale(name: str, pairs: pd.DataFrame) -> dict:
    """核验 4.1.3 与表 5-1 的规模常数：|U|、|I|、|E|、稀疏度、人均交互。"""
    n_users = pairs["user_id"].nunique()
    n_items = pairs["item_id"].nunique()
    n_pairs = len(pairs)
    out = {
        "|U| 用户数": f"{n_users:,}",
        "|I| 商品数": f"{n_items:,}",
        "|E| 交互对数": f"{n_pairs:,}",
        "稀疏度": f"{1 - n_pairs / (n_users * n_items):.4%}",
        "人均交互": f"{n_pairs / n_users:.2f}",
    }
    if name == "AJ":
        # AJ 的 |A|（行为记录数）≠ |E|（对数），4.1.3 需据此说明
        n_recs = sum(len(pd.read_csv(PROCESSED_DIR / name / f"{s}.csv",
                                     usecols=["user_id"]))
                     for s in ("train", "val", "test"))
        out["|A| 行为记录数"] = f"{n_recs:,}"
    return out


def check_rating_dist(name: str, pairs: pd.DataFrame) -> dict:
    """核验 4.1.1 局限一引用的评分分布（仅 Amazon 有 rating，AJ 无）。"""
    if "rating" not in pairs.columns:
        return {"说明": f"{name} 无 rating 字段，4.1.1 的评分分布论据不适用；"
                        "AJ 的边权重由原生 action_type 折算"}
    dist = pairs["rating"].value_counts(normalize=True).sort_index()
    return {f"{int(r)}分": f"{p:.1%}" for r, p in dist.items()}


def check_tail(pairs: pd.DataFrame) -> dict:
    """
    核验 4.1.4 的长尾描述：前 20% 商品交互占比、长尾商品占比与承载量。

    补算「覆盖 80% 交互所需商品比例」——单看前 20% 占比无法判断长尾强度，
    IS 的 56.5% 实际弱于 TH/OP/AJ，4.1.4 据此用「中度长尾」而非「明显长尾」。
    """
    deg = pairs["item_id"].value_counts()
    n_items, n_pairs = len(deg), len(pairs)
    d = np.sort(deg.to_numpy())[::-1]
    top20 = max(1, int(n_items * 0.2))
    tail = deg[deg < TAIL_DEG]
    cum = np.cumsum(d) / d.sum()
    k80 = int(np.searchsorted(cum, 0.8) + 1)

    # Gini 用于跨数据集比较集中度，越接近 0 越均匀
    x = np.sort(deg.to_numpy())
    n = len(x)
    gini = 1 - 2 * np.sum(np.cumsum(x)) / (n * np.cumsum(x)[-1]) + 1 / n

    return {
        "前20%商品交互占比": f"{d[:top20].sum() / n_pairs:.2%}",
        "覆盖80%交互所需商品": f"{k80:,} 个 ({k80 / n_items:.1%})",
        "长尾商品占比": f"{len(tail) / n_items:.2%}（{len(tail):,} 个）",
        "长尾商品承载交互": f"{tail.sum() / n_pairs:.2%}",
        "商品度中位数": f"{deg.median():.0f}",
        "Gini 系数": f"{gini:.4f}",
    }


def check_lambda(pairs: pd.DataFrame) -> pd.DataFrame:
    """
    复算式(4-1) 在 λ=0.1/0.01/0.001 下的边权重分布，核验 4.1.2 与 5.8.1。

    IS 时间跨度 22.1 年、交互年龄中位 1347 天（3.7 年）；λ=0.1 的半衰期仅 6.9 天，
    会把绝大多数边压到 1e-6 以下，等同丢弃图结构——这是论文取 0.001 的直接依据。
    AJ 无 rating，改用其预处理产物 edges.csv 的实际权重分布无法反推 α，
    故此处对无 rating 的数据集退化为「按 α=1 计算时间衰减因子」的对比。
    """
    t_now = pairs["timestamp"].max()
    age_days = ((t_now - pairs["timestamp"]) / SECONDS_PER_DAY).to_numpy()
    if "rating" in pairs.columns:
        alpha = pairs["rating"].map(RATING_ALPHA).to_numpy()
        alpha_note = ""
    else:
        alpha = np.ones(len(pairs))
        alpha_note = "（无 rating，α 取 1，仅看时间衰减因子）"

    rows = []
    for lam in (0.1, 0.01, 0.001):
        w = alpha * np.exp(-lam * age_days)
        rows.append({
            "λ": lam,
            "半衰期(天)": f"{np.log(2) / lam:.1f}",
            "半衰期(年)": f"{np.log(2) / lam / 365.25:.2f}",
            "权重<1e-6占比": f"{(w < 1e-6).mean():.2%}",
            "权重中位数": f"{np.median(w):.4f}",
            "权重最小值": f"{w.min():.2e}",
        })
    df = pd.DataFrame(rows)
    if alpha_note:
        df.attrs["note"] = alpha_note
    return df


def check_time_span(pairs: pd.DataFrame) -> dict:
    """核验 4.1.1 局限二与 5.8.1 引用的时间跨度与交互年龄。"""
    t_min, t_max = pairs["timestamp"].min(), pairs["timestamp"].max()
    age_days = (t_max - pairs["timestamp"]) / SECONDS_PER_DAY
    return {
        "起": pd.to_datetime(t_min, unit="s").strftime("%Y-%m-%d"),
        "止": pd.to_datetime(t_max, unit="s").strftime("%Y-%m-%d"),
        "跨度(年)": f"{(t_max - t_min) / SECONDS_PER_DAY / 365.25:.1f}",
        "交互年龄中位(天)": f"{age_days.median():.0f}",
    }


# =====================================================================
# 三、入口
# =====================================================================


def run(name: str, sections: list[str]) -> None:
    """对单个数据集执行选定小节的核验并打印。"""
    pairs = load_pairs(name)
    print(f"\n{'=' * 74}\n{name}\n{'=' * 74}")

    checks = {
        "scale": ("4.1.3 / 表5-1 规模与稀疏度", lambda: check_scale(name, pairs)),
        "rating": ("4.1.1 局限一 评分分布", lambda: check_rating_dist(name, pairs)),
        "tail": ("4.1.4 长尾分布", lambda: check_tail(pairs)),
        "span": ("4.1.1 局限二 / 5.8.1 时间跨度", lambda: check_time_span(pairs)),
    }
    for key, (title, fn) in checks.items():
        if sections and key not in sections:
            continue
        print(f"\n【{title}】")
        for k, v in fn().items():
            print(f"  {k:<22}{v}")

    if not sections or "lambda" in sections:
        print("\n【4.1.2 / 5.8.1 式(4-1) λ 衰减对比】")
        lam_tbl = check_lambda(pairs)
        print(lam_tbl.to_string(index=False))
        if note := lam_tbl.attrs.get("note"):
            print(f"  {note}")


def main() -> None:
    ap = argparse.ArgumentParser(description="论文 4.1 节数据口径核验")
    ap.add_argument("datasets", nargs="*", default=["IS"],
                    help="数据集短名，默认 IS")
    ap.add_argument("--section", nargs="*",
                    choices=["scale", "rating", "tail", "span", "lambda"],
                    help="只跑指定小节，缺省全跑")
    args = ap.parse_args()
    for name in args.datasets:
        run(name, args.section or [])


if __name__ == "__main__":
    main()
