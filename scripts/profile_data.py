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
# 默认只给主实验数据集画图；其余数据集只算 JSON
DEFAULT_FIGURES = {"IS"}


# --------------------------------------------------------------------------- 画像计算
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

    # ---------------- 交互年龄（天）：以训练集最大时间戳为参照
    t_now = int(train["timestamp"].max())
    ages_days = (t_now - train["timestamp"].to_numpy(dtype=np.int64)) / SEC_PER_DAY

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
        rating_dist = (
            train["rating"].value_counts().sort_index().astype(int).to_dict()
        )
    else:
        rating_nunique = None
        all_same_ratio = None
        rating_dist = None

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
            "t_now": t_now,
            "definition": "训练集最大时间戳减去交互时间戳，单位天；"
            "t_now 取该数据集训练集 timestamp 最大值",
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
    ax.set_ylabel("训练交互数")
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


def plot_inter_gap(profile: dict, ax) -> None:
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
    med = profile["inter_gap_days"]["median"]
    ax.axvline(med, color="#C92A2A", linestyle="--", linewidth=1)
    ax.text(med, ax.get_ylim()[1] * 0.92, f" 中位数 {med:.1f} 天",
            color="#C92A2A", fontsize=8, va="top")


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

    # 单图各一张（便于单独插入论文）
    single = {
        "rating_dist": plot_rating_distribution,
        "train_pairs_per_user": plot_train_pairs_per_user,
        "inter_gap": plot_inter_gap,
        "test_item_in_train": plot_test_item_in_train,
        "user_rating_variety": plot_user_rating_variety,
    }
    for name, fn in single.items():
        fig, ax = plt.subplots(figsize=(W_SINGLE, 6 * 1 / 2.54))
        fn(profile, ax)
        written += save_fig(fig, out_dir / f"{ds}_{name}")
        plt.close(fig)

    # 五联总图（2×3，末位留空）
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