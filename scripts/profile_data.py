"""数据画像与 γ₀、λ₀ 取值依据（S0-b）

只读 data/processed/{DS}/，产出：
    results/profile/{IS,TH,OP}.json     供论文与后续模型初始化使用
    figures/profile/*.svg|*.png         IS 的 5 张画像图

γ₀、λ₀ 的定义
-------------
    相邻交互间隔中位数  Δ̄（天）：同一用户按时间排序后相邻两条训练交互的时间间隔
    训练集交互年龄中位数 Ā（天）：以训练集最大时间戳为参照，各训练交互的年龄
    γ₀ = ln2 / Δ̄      —— 注意力时间衰减率的先验：使注意力权重在 Δ̄ 天后衰减一半
    λ₀ = ln2 / Ā      —— 边权时间衰减率的先验：使边权重在 Ā 天后衰减一半

    两者都取 ln2 / 中位数，即"半衰期 = 中位数"的自然取值，不依赖人工调参。
    论文第 4 章用它们替代 V8 的 γ=0.3、λ=0.001 经验值。

口径
----
    - 交互间隔只统计同一用户相邻两条训练交互，跨用户不计
    - 间隔单位天 = Δ秒 / 86400
    - 年龄以该数据集训练集 timestamp 最大值（T_now）为参照
    - 用户训练交互数、评分分布、测试覆盖等均按训练集/测试集原始行统计

用法：
    python scripts/profile_data.py                 # 默认 IS
    python scripts/profile_data.py IS TH OP        # 多数据集
    python scripts/profile_data.py --figures       # 强制为所有数据集画图（默认仅 IS）

与相邻脚本的分工：
    data/prepare_data.py      产出 processed/，本脚本只读
    data/verify_5_1_data.py   表 5-1 数据集统计
    本脚本                    数据画像、γ₀/λ₀ 取值依据、画像图
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
RESULTS_DIR = REPO_ROOT / "results" / "profile"
FIGURES_DIR = REPO_ROOT / "figures" / "profile"

SEC_PER_DAY = 86400
# 3.3.4 长尾阈值：训练图内交互次数 < 10 记为长尾商品
TAIL_DEG = 10
# 表3-1 评分 → 反馈强度权重 α_r
ALPHA_BY_RATING = {5: 3.0, 4: 1.5, 3: 1.0, 2: 0.1, 1: 0.1}
# 默认只给主实验数据集画图；其余数据集只算 JSON
DEFAULT_FIGURES = {"IS"}
# 表3-11 冷启动分层（训练集交互数区间）
LAYERS = {"0~4 条": (0, 4), "5~9 条": (5, 9),
          "10~29 条": (10, 29), "≥30 条": (30, 10 ** 9)}


# --------------------------------------------------------------------------- 画像计算
def tail_summary(deg_train: pd.Series, deg_full: pd.Series) -> dict:
    """长尾汇总：阈值 θ=10（与 V9 3.3.4 一致），正文用训练图口径。

    返回 tail_train.* 的标量（供 numbers.json）+ 两条累计曲线（供图3-4）。
    """
    def _stats(deg: pd.Series) -> dict:
        d = np.sort(deg.to_numpy())[::-1]
        n_items = len(d)
        total = d.sum()
        tail = deg[deg < TAIL_DEG]
        k20 = max(int(n_items * 0.2), 1)
        curve = np.cumsum(d) / total
        j80 = int(np.searchsorted(curve, 0.8)) + 1
        return {
            "n_items": int(n_items),
            "top20_pair_share": float(d[:k20].sum() / total),
            "tail_item_ratio": float(len(tail) / n_items),
            "tail_pair_share": float(tail.sum() / total),
            "cover80_item_ratio": float(min(j80, n_items) / n_items),
            "curve": curve.tolist(),
        }

    t, f = _stats(deg_train), _stats(deg_full)
    # 拆分出图片用的字段名（tail_train 内的标量键直接进 numbers.json）
    return {
        "tail_train": {k: v for k, v in t.items() if k != "curve"},
        "tail_full": {k: v for k, v in f.items() if k != "curve"},
        "curve_train": t["curve"],
        "curve_full": f["curve"],
    }


def compute_profile(ds: str) -> dict:
    """读 processed/{ds}/，返回画像指标字典。不写文件。"""
    stats_path = PROCESSED_DIR / ds / "stats.json"
    if not stats_path.exists():
        raise FileNotFoundError(f"缺少 {stats_path}，无法核对口径")

    with open(stats_path, encoding="utf-8") as f:
        stats = json.load(f)

    train = pd.read_parquet(PROCESSED_DIR / ds / "train.parquet")
    test = pd.read_parquet(PROCESSED_DIR / ds / "test.parquet")
    val = pd.read_parquet(PROCESSED_DIR / ds / "val.parquet")

    # ---------------- 规模（用于断言与论文引用）
    # 口径与 stats.json / verify_5_1 一致：train∪val∪test 合并后按 (user, item) 唯一对统计。
    # AJ 的行为行含多 action，同一对会出现多行，故必须去重。
    all_split = pd.concat(
        [train[["user_id", "item_id"]],
         val[["user_id", "item_id"]],
         test[["user_id", "item_id"]]]
    ).drop_duplicates()
    n_users = int(all_split["user_id"].nunique())
    n_items_total = int(all_split["item_id"].nunique())
    n_pairs = int(len(all_split))

    # ---------- 两种口径的说明
    # 正文口径（V9 3.1 / 图3-1~3-5 / 3.3.4 / 3.5.4）= **训练集对**：
    #   训练图只由训练集构建（3.2/3.3.6），画像描述的就是模型看到的那张图。
    # 数据集口径（表3-3 / 3.5.1）= **全量对**：
    #   train∪val∪test 去重后的整体规模，仅用于数据集统计，不做画像。
    full_cols = [c for c in ("user_id", "item_id", "timestamp", "rating")
                 if c in train.columns]
    train_pairs = train[full_cols].drop_duplicates(["user_id", "item_id"])

    # 全量对（含 timestamp / rating）—— 仅保留给数据集口径的诊断字段
    all_pairs = pd.concat([train[full_cols], val[full_cols], test[full_cols]]) \
        .drop_duplicates(["user_id", "item_id"])

    # ---------------- 训练集每用户交互数
    per_user = train.groupby("user_id").size()

    # ---------------- 相邻交互间隔（天）：同一用户按时间排序后的差分
    #   只保留正间隔，同一秒内的多条交互不计入分母
    sorted_train = train[["user_id", "timestamp"]].sort_values(
        ["user_id", "timestamp"], kind="mergesort"
    )
    gaps = sorted_train.groupby("user_id")["timestamp"].diff()
    gaps = gaps[gaps.notna() & (gaps > 0)]
    gaps_days = gaps.to_numpy(dtype=np.float64) / SEC_PER_DAY

    # ---------------- 交互年龄（天）
    # 正文口径 = 训练集对，T_now = 训练集最大时间戳；与图3-5 的边权年龄一致。
    # interaction_age_full_days 只作数据集口径诊断，不进正文。
    t_now = int(train_pairs["timestamp"].max())
    ages_days = (t_now - train_pairs["timestamp"].to_numpy(dtype=np.int64)) / SEC_PER_DAY
    ages_q = np.percentile(ages_days, [25, 50, 75]).tolist()
    t_ref = int(all_pairs["timestamp"].max())
    ages_full = (t_ref - all_pairs["timestamp"].to_numpy(dtype=np.int64)) / SEC_PER_DAY
    age_q = np.percentile(ages_full, [25, 50, 75]).tolist()

    # ---------------- γ₀、λ₀（半衰期 = 中位数）
    gap_median = float(np.median(gaps_days))
    age_median = float(np.median(ages_days))
    gamma0 = float(np.log(2) / gap_median) if gap_median > 0 else None
    lambda0 = float(np.log(2) / age_median) if age_median > 0 else None

    # ---------------- 测试物品是否在训练集出现过
    train_items = set(train["item_id"].to_numpy().tolist())
    test_in_train = test["item_id"].isin(train_items)
    test_item_in_train_ratio = float(test_in_train.mean())

    # ---------------- 用户内评分是否全部相同（只用训练集）
    has_rating = "rating" in train.columns
    if has_rating:
        rating_nunique = train.groupby("user_id")["rating"].nunique()
        all_same_ratio = float((rating_nunique == 1).mean())
        # 正文口径（图3-1 / 3.1 / 3.5.3 / 3.6）= 训练集对
        rating_dist = (
            train_pairs["rating"].value_counts().sort_index().astype(int).to_dict()
        )
        # 数据集口径（表3-3 相关描述）—— 仅诊断用
        rating_dist_full = (
            all_pairs["rating"].value_counts().sort_index().astype(int).to_dict()
        )
    else:
        rating_nunique = None
        all_same_ratio = None
        rating_dist = None
        rating_dist_full = None

    # ---------------- 长尾（训练图，对应图3-4 / 3.3.4）
    # 商品度按训练集对统计（训练图里商品只有训练集的边）；
    # 另存全量对曲线供对照，进正文的只有 train 口径。
    tail = tail_summary(train_pairs["item_id"].value_counts(),
                        all_pairs["item_id"].value_counts())
    tail_curve_train = tail.pop("curve_train")
    tail_curve_full = tail.pop("curve_full")

    # ---------------- 式(3-1) λ 敏感性（训练图，对应图3-5 / 3.5.4）
    # 同一套 α_r + 训练集对年龄，只换 λ；用于说明 λ=0.1 会把边权压到 1e-6 以下。
    if has_rating:
        alpha_tr = train_pairs["rating"].map(ALPHA_BY_RATING).to_numpy(dtype=np.float64)
    else:
        alpha_tr = np.ones(len(train_pairs))
    age_tr = (t_now - train_pairs["timestamp"].to_numpy(dtype=np.int64)) / SEC_PER_DAY
    lambda_sens = {}
    for lam in (0.1, 0.01, 0.001):
        w = alpha_tr * np.exp(-lam * age_tr)
        lambda_sens[f"lambda_{str(lam).replace('.', 'p')}"] = {
            "half_life_days": float(np.log(2) / lam),
            "near_zero_ratio": float((w < 1e-6).mean()),
            "median_weight": float(np.median(w)),
            "min_weight": float(w.min()),
        }

    return {
        "dataset": ds,
        "scale": {
            "num_users": n_users,
            "num_items": n_items_total,
            "num_pairs": n_pairs,
        },
        "stats_json_scale": {
            "num_users": int(stats["num_users"]),
            "num_items": int(stats["num_items"]),
            "num_pairs": int(stats["num_pairs"]),
        },
        "train_pairs_per_user": {
            "median": float(per_user.median()),
            "mean": float(per_user.mean()),
            "min": int(per_user.min()),
            "max": int(per_user.max()),
            "n_users": int(len(per_user)),
        },
        "inter_gap_days": {
            "median": gap_median,
            "mean": float(np.mean(gaps_days)),
            "p90": float(np.percentile(gaps_days, 90)),
            "n_gaps": int(len(gaps_days)),
            "definition": "同一用户按时间排序后相邻两条训练交互的间隔，单位天；"
            "同一秒内的多条交互不计入",
        },
        "interaction_age_days": {
            "median": age_median,
            "mean": float(np.mean(ages_days)),
            "p25": float(ages_q[0]),
            "p75": float(ages_q[2]),
            "t_now": t_now,
            "definition": "训练集对口径（正文口径，图3-5）：训练集最大时间戳减去交互时间戳，"
            "单位天；t_now 取该数据集训练集 timestamp 最大值",
        },
        "interaction_age_full_days": {
            "median": float(np.median(ages_full)),
            "mean": float(np.mean(ages_full)),
            "p25": float(age_q[0]),
            "p75": float(age_q[2]),
            "t_ref": t_ref,
            "definition": "全量对（train∪val∪test，按对去重）口径，仅作数据集层面诊断，"
            "不进正文、不进图3-5",
        },
        "gamma0": {
            "value": gamma0,
            "formula": "ln2 / 相邻交互间隔中位数（天）",
            "interpretation": "注意力权重在间隔中位数天数后衰减一半",
        },
        "lambda0": {
            "value": lambda0,
            "formula": "ln2 / 训练集交互年龄中位数（天）",
            "interpretation": "边权重在年龄中位数天数后衰减一半",
        },
        "test_item_in_train_ratio": {
            "value": test_item_in_train_ratio,
            "n_test": int(len(test)),
            "definition": "测试行的物品在训练集出现过的比例",
        },
        "user_all_same_rating_ratio": {
            "value": all_same_ratio,
            "definition": "训练集中一个用户所有交互评分相同的用户占比"
            if has_rating
            else "该数据集无 rating 字段，不适用",
        },
        "rating_distribution_train": rating_dist,
        "rating_distribution_full": rating_dist_full,
        "tail_train": tail["tail_train"],
        "tail_full": tail["tail_full"],
        "tail_curve_train": tail_curve_train,
        "tail_curve_full": tail_curve_full,
        "lambda_sens": lambda_sens,
        "has_rating": has_rating,
    }


def assert_scale(profile: dict) -> None:
    """断言画像规模与 stats.json 一致。不一致直接抛错，不继续写文件。"""
    got = profile["scale"]
    want = profile["stats_json_scale"]
    for k in ("num_users", "num_items", "num_pairs"):
        if got[k] != want[k]:
            raise AssertionError(
                f"{profile['dataset']} {k} 不一致：画像 {got[k]:,} / stats.json {want[k]:,}"
            )
    print(f"  ✅ {profile['dataset']} 规模与 stats.json 一致"
          f"（{got['num_users']:,} 用户 / {got['num_items']:,} 物品 / {got['num_pairs']:,} 交互）")


# --------------------------------------------------------------------------- 绘图
def plot_rating_distribution(profile: dict, ax) -> None:
    # 正文口径（V9 3.1 / 图3-1）= 训练集对（训练图上的评分分布）。
    dist = profile["rating_distribution_train"]
    if not dist:
        ax.text(0.5, 0.5, "该数据集无评分字段", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_axis_off()
        return
    ratings = list(dist.keys())
    counts = np.array([dist[r] for r in ratings], dtype=float)
    total = counts.sum()
    bars = ax.bar([str(r) for r in ratings], counts, color="#4C6EF5", width=0.62)
    for bar, c in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, c, f"{c / total:.1%}",
                ha="center", va="bottom", fontsize=8)
    ax.set_xlabel("评分")
    ax.set_ylabel("训练交互对数")
    ax.set_title("(a) 评分分布")


def plot_train_pairs_per_user(profile: dict, ax) -> None:
    # 需要原始每用户计数；从返回值里的统计无法反推分布，故重读一次（内存已缓存页）
    train = pd.read_parquet(PROCESSED_DIR / profile["dataset"] / "train.parquet",
                            columns=["user_id"])
    per_user = train.groupby("user_id").size().to_numpy()
    bins = np.logspace(0, np.log10(per_user.max() + 1), 40)
    ax.hist(per_user, bins=bins, color="#F08C00", edgecolor="white", linewidth=0.3)
    ax.set_xscale("log")
    ax.set_xlabel("每用户训练交互数（对数坐标）")
    ax.set_ylabel("用户数")
    ax.set_title("(b) 用户训练交互数分布")
    ax.axvline(profile["train_pairs_per_user"]["median"], color="#C92A2A",
               linestyle="--", linewidth=1)
    ax.text(profile["train_pairs_per_user"]["median"], ax.get_ylim()[1] * 0.92,
            f" 中位数 {profile['train_pairs_per_user']['median']:.0f}",
            color="#C92A2A", fontsize=8, va="top")
    # 图3-2 需标出四层分层阈值与各层占比（与表3-11 同口径）
    ymax = ax.get_ylim()[1]
    for x in (5, 10, 30):
        ax.axvline(x, color="#868E96", linestyle=":", linewidth=0.8)
    for x, label, y in ((1.05, "0~4 条", 0.60),
                        (5.3, "5~9 条", 0.40),
                        (10.3, "10~29 条", 0.26),
                        (30.5, "≥30 条", 0.14)):
        lo, hi = LAYERS[label]
        share = ((per_user >= lo) & (per_user <= hi)).sum() / len(per_user)
        ax.text(x, ymax * y, f"{label} {share:.1%}", fontsize=7,
                color="#868E96", va="center")


def plot_inter_gap(profile: dict, ax) -> None:
    # 图3-3 需要四分位标注，故用原始间隔现算分位数
    train = pd.read_parquet(PROCESSED_DIR / profile["dataset"] / "train.parquet",
                            columns=["user_id", "timestamp"])
    sorted_train = train.sort_values(["user_id", "timestamp"], kind="mergesort")
    gaps = sorted_train.groupby("user_id")["timestamp"].diff()
    gaps = gaps[gaps.notna() & (gaps > 0)].to_numpy(dtype=np.float64) / SEC_PER_DAY
    lo = max(gaps[gaps > 0].min(), 1e-3)
    bins = np.logspace(np.log10(lo), np.log10(gaps.max()), 50)
    ax.hist(gaps, bins=bins, color="#2F9E44", edgecolor="white", linewidth=0.3)
    ax.set_xscale("log")
    ax.set_xlabel("相邻交互间隔（天，对数坐标）")
    ax.set_ylabel("交互对数")
    ax.set_title("(c) 用户内相邻交互间隔分布")
    q1, med, q3 = np.percentile(gaps, [25, 50, 75])
    ymax = ax.get_ylim()[1]
    for v, ls in ((q1, ":"), (med, "--"), (q3, ":")):
        ax.axvline(v, color="#C92A2A", linestyle=ls, linewidth=1)
    # 图3-3 需标注中位数与四分位数
    for v, label, y in ((q1, "Q1", 0.45), (med, "中位数", 0.92), (q3, "Q3", 0.30)):
        ax.text(v, ymax * y, f" {label} {v:.2f} 天",
                color="#C92A2A", fontsize=7, va="center")


def plot_item_tail(profile: dict, ax) -> None:
    """(d) 商品交互长尾：按交互次数降序的累计交互占比（训练图，图3-4）。

    正文口径（V9 3.3.4）= 训练集对：前 20% 商品覆盖 57.2% 交互；交互 <10 的商品
    占 65.8%、承载 29.2% 交互；覆盖 80% 交互需 47.9% 商品。
    """
    y = np.asarray(profile["tail_curve_train"], dtype=float)
    if y.size == 0:
        ax.set_axis_off()
        return
    x = np.arange(1, y.size + 1) / y.size
    ax.plot(x, y, color="#4C6EF5", linewidth=1.4)
    # 前 20% 商品
    i20 = max(int(0.2 * y.size) - 1, 0)
    ax.axvline(0.2, color="#868E96", linestyle=":", linewidth=0.8)
    ax.plot([0.2], [y[i20]], "o", color="#C92A2A", markersize=4)
    ax.annotate(f"前20%覆盖 {y[i20]:.1%}", xy=(0.2, y[i20]),
                xytext=(0.32, y[i20] - 0.18), fontsize=8, color="#C92A2A",
                arrowprops=dict(arrowstyle="-", color="#C92A2A", linewidth=0.7))
    # 覆盖 80% 交互所需商品比例
    j = int(np.searchsorted(y, 0.8))
    if j < y.size:
        ax.axhline(0.8, color="#868E96", linestyle=":", linewidth=0.8)
        ax.plot([x[j]], [0.8], "o", color="#2F9E44", markersize=4)
        ax.annotate(f"{x[j]:.1%} 商品覆盖 80%", xy=(x[j], 0.8),
                    xytext=(max(x[j] - 0.35, 0.05), 0.62), fontsize=8,
                    color="#2F9E44",
                    arrowprops=dict(arrowstyle="-", color="#2F9E44", linewidth=0.7))
    # 长尾切点：交互次数 <10 的商品（站 65.8%）仅承载 29.2% 交互
    tail = profile["tail_train"]
    # 文档口径：长尾商品占比 65.8%，承载 29.2% 交互（训练图）
    tail_share = tail["tail_item_ratio"]
    tail_inter = tail["tail_pair_share"]
    # 曲线上的点 = (top 商品占比, 它们承载的交互占比) = (1 - 长尾占比, 1 - 长尾承载)
    ax.axvline(1.0 - tail_share, color="#7048E8", linestyle=":", linewidth=0.8)
    ax.axhline(1.0 - tail_inter, color="#7048E8", linestyle=":", linewidth=0.8)
    ax.plot([1.0 - tail_share], [1.0 - tail_inter], "o",
            color="#7048E8", markersize=4)
    ax.annotate(f"<10次商品 {tail_share:.1%}\n承载 {tail_inter:.1%} 交互",
                xy=(1.0 - tail_share, 1.0 - tail_inter),
                xytext=(0.05, 0.72), fontsize=7, color="#7048E8",
                arrowprops=dict(arrowstyle="-", color="#7048E8", linewidth=0.7))
    ax.set_xlabel("商品（按交互次数降序，累计占比）")
    ax.set_ylabel("累计交互占比")
    ax.set_title("(d) 商品交互长尾分布")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)


def plot_edge_weight(profile: dict, ax) -> None:
    """(e) 边权重 w(u,i) 按数量级分桶的占比：λ=0.001（采用值）与 λ=0.1（消费品常用值）（图3-5）。

    口径 = 训练图（与 edges.csv 同源）：只用训练集对，T_now 取训练集最大时间戳，
    α_r 按表3-1 映射。用数量级分桶而非连续直方图，是因为正文要说明的是
    「λ=0.1 时绝大多数边权重低于 1e-6」——分桶后该比例可直接读出。
    """
    ds = profile["dataset"]
    cols = ["user_id", "item_id", "timestamp"]
    train = pd.read_parquet(PROCESSED_DIR / ds / "train.parquet",
                            columns=cols + (["rating"] if profile["has_rating"] else []))
    pairs = train.drop_duplicates(["user_id", "item_id"])
    ages = (pairs["timestamp"].max() - pairs["timestamp"].to_numpy(dtype=np.int64)) \
        / SEC_PER_DAY
    if profile["has_rating"]:
        alpha = pairs["rating"].map(ALPHA_BY_RATING).to_numpy(dtype=np.float64)
    else:
        alpha = np.ones(len(pairs))

    # 数量级分桶：<1e-12 / 1e-12~1e-9 / 1e-9~1e-6 / 1e-6~1e-3 / 1e-3~1e-1 / ≥1e-1
    edges = [-np.inf, -12, -9, -6, -3, -1, np.inf]
    labels = ["<1e-12", "1e-12~1e-9", "1e-9~1e-6", "1e-6~1e-3", "1e-3~1e-1", "≥1e-1"]
    series = []
    for lam in (0.001, 0.1):
        w = alpha * np.exp(-lam * ages)
        x = np.log10(np.clip(w, 1e-330, None))
        cnt, _ = np.histogram(x, bins=edges)
        series.append(cnt / cnt.sum())

    idx = np.arange(len(labels))
    width = 0.38
    r001 = profile["lambda_sens"]["lambda_0p001"]["near_zero_ratio"]
    r01 = profile["lambda_sens"]["lambda_0p1"]["near_zero_ratio"]
    ax.bar(idx - width / 2, series[0], width, color="#4C6EF5",
           label=f"λ=0.001（<1e-6 占 {r001:.1%}）")
    ax.bar(idx + width / 2, series[1], width, color="#C92A2A",
           label=f"λ=0.1（<1e-6 占 {r01:.1%}）")
    ax.set_xticks(idx)
    ax.set_xticklabels(labels, fontsize=7, rotation=30)
    # 1e-6 分界线的位置（第 2、3 桶之间）
    ax.axvline(2.5, color="#868E96", linestyle=":", linewidth=0.9)
    ax.text(2.55, 0.10, "w=1e-6", fontsize=7, color="#868E96")

    ax.set_xlabel("边权重区间")
    ax.set_ylabel("边占比")
    ax.set_ylim(0, 1.0)
    ax.set_title("(e) 边权重分布（两档 λ）")
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.52, 1.0))


def plot_test_item_in_train(profile: dict, ax) -> None:
    ratio = profile["test_item_in_train_ratio"]["value"]
    ax.bar(["出现过", "未出现"], [ratio, 1 - ratio],
           color=["#2F9E44", "#C92A2A"], width=0.55)
    for i, v in enumerate([ratio, 1 - ratio]):
        ax.text(i, v, f"{v:.2%}", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("测试行占比")
    ax.set_title("(d) 测试物品在训练集是否出现")


def plot_user_rating_variety(profile: dict, ax) -> None:
    if not profile["has_rating"]:
        ax.text(0.5, 0.5, "该数据集无评分字段", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_axis_off()
        return
    train = pd.read_parquet(PROCESSED_DIR / profile["dataset"] / "train.parquet",
                            columns=["user_id", "rating"])
    nunique = train.groupby("user_id")["rating"].nunique()
    counts = nunique.value_counts().sort_index()
    ax.bar([str(k) for k in counts.index], counts.to_numpy(),
           color="#7048E8", width=0.6)
    ax.set_xlabel("用户内不同评分个数")
    ax.set_ylabel("用户数")
    ax.set_title("(e) 用户内评分是否全部相同")
    same = profile["user_all_same_rating_ratio"]["value"]
    ax.text(0.98, 0.95, f"全相同 {same:.1%}", transform=ax.transAxes,
            ha="right", va="top", fontsize=9)


def draw_figures(profile: dict) -> list[Path]:
    """画 5 张画像图，返回写出的文件路径列表。"""
    import matplotlib.pyplot as plt

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from plot_style import W_DOUBLE, W_SINGLE, apply_style, save_fig

    apply_style()
    ds = profile["dataset"]
    out_dir = FIGURES_DIR
    written: list[Path] = []

    # 只导出 V9 图3-1~3-5 需要的五张；test_item_in_train / user_rating_variety
    # 保留函数但不导出（不在 V9 的图目录中，见 data/README.md §6 第 9 条）
    single = {
        "fig3-1_rating_dist": plot_rating_distribution,
        "fig3-2_train_pairs_per_user": plot_train_pairs_per_user,
        "fig3-3_inter_gap": plot_inter_gap,
        "fig3-4_item_tail": plot_item_tail,
        "fig3-5_edge_weight": plot_edge_weight,
    }
    for name, fn in single.items():
        fig, ax = plt.subplots(figsize=(W_SINGLE, 6 * 1 / 2.54))
        fn(profile, ax)
        written += save_fig(fig, out_dir / f"{ds}_{name}")
        plt.close(fig)

    # 五联总图（1×5 太窄，用 2×3、末位留空），仅作速览，不直接进论文
    fig, axes = plt.subplots(2, 3, figsize=(W_DOUBLE, 8 * 1 / 2.54))
    for ax, fn in zip(axes.flat, single.values()):
        fn(profile, ax)
    axes.flat[-1].set_axis_off()
    fig.tight_layout()
    written += save_fig(fig, out_dir / f"{ds}_all")
    plt.close(fig)

    return written


# --------------------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser(description="数据画像与 γ₀、λ₀ 取值依据")
    ap.add_argument("datasets", nargs="*", default=["IS"],
                    help="数据集代码（默认 IS）")
    ap.add_argument("--figures", nargs="*", default=None,
                    help="为指定数据集画图（默认仅 IS）")
    args = ap.parse_args()

    datasets = args.datasets or ["IS"]
    figure_sets = set(args.figures) if args.figures is not None else DEFAULT_FIGURES

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for ds in datasets:
        print(f"== {ds} ==")
        profile = compute_profile(ds)
        assert_scale(profile)

        out = RESULTS_DIR / f"{ds}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        print(f"  → {out.relative_to(REPO_ROOT)}")

        g0 = profile["gamma0"]["value"]
        l0 = profile["lambda0"]["value"]
        print(f"  γ₀ = ln2 / {profile['inter_gap_days']['median']:.2f} 天 = {g0:.6f} / 天")
        print(f"  λ₀ = ln2 / {profile['interaction_age_days']['median']:.1f} 天 = {l0:.6f} / 天")

        if ds in figure_sets:
            written = draw_figures(profile)
            print(f"  → {len(written)} 个图文件写入 {FIGURES_DIR.relative_to(REPO_ROOT)}/")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())