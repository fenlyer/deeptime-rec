"""配对检验（S1-c）

比较两个模型在同一批用户上的指标差异，以用户为单位做配对检验。

口径
----
    样本单位是「用户」，不是 seed。V8 5.5.3 用 t(4)（按 4 个 seed 做检验）是错的：
    5 个 seed 只是对同一个用户多次估计的重复测量，用 4 个自由度检验功效极低，
    且把 seed 噪声当成总体差异。本模块改为：
        1. 每个用户跨 seed 取平均，得到该用户对模型 A / B 的稳定估计；
        2. 在用户集合的交集上做配对 t 检验与 Wilcoxon 符号秩检验；
        3. 效应量 d_z = t / sqrt(n)，n 为用户数（不是 seed 数）。

    指标取 Recall@K 或 NDCG@K，由 ranks 直接换算，与 eval/metrics.py 一致。

用法：
    python -m eval.paired_test \
        --dir-a results/recall_main/ti_lightgcn --dir-b results/recall_main/lightgcn \
        --k 10 --metric Recall --output results/recall_main/paired_ti_vs_lg.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd
from scipy import stats as sps


# --------------------------------------------------------------------------- 指标换算
def rank_to_metric(ranks: dict[str, float], k: int, metric: str) -> dict[str, float]:
    """把 {user_id: rank} 换成 {user_id: 指标值}，逐用户计算。

    Recall@K: 1(rank<=K)
    NDCG@K  : 1(rank<=K) / log2(rank+1)   （LOO 下 IDCG=1）
    """
    out: dict[str, float] = {}
    if metric.lower() == "recall":
        for u, r in ranks.items():
            out[u] = 1.0 if r <= k else 0.0
    elif metric.lower() == "ndcg":
        for u, r in ranks.items():
            out[u] = (1.0 / math.log2(r + 1)) if r <= k else 0.0
    else:
        raise ValueError(f"未知指标 {metric}，可选 Recall / NDCG")
    return out


def _metric_name(metric: str, k: int) -> str:
    canonical = {"recall": "Recall", "ndcg": "NDCG"}.get(metric.lower())
    if canonical is None:
        raise ValueError(f"未知指标 {metric}，可选 Recall / NDCG")
    return f"{canonical}@{k}"


# --------------------------------------------------------------------------- 聚合
def _average_over_seeds(dfs: list[pd.DataFrame]) -> pd.Series:
    """多个 seed 的 per_user 表 → 每用户平均 rank。

    以 user_id 为索引；缺失用户在某个 seed 上不参与平均（对齐后交给交集处理）。
    """
    frames = [d.set_index("user_id")["rank"].astype(float) for d in dfs]
    merged = pd.concat(frames, axis=1)
    return merged.mean(axis=1)


def _load_per_user_dirs(model_dir: Path) -> list[pd.DataFrame]:
    """读 results/{exp}/{model}/seed*/per_user.parquet。"""
    paths = sorted(Path(model_dir).glob("seed*/per_user.parquet"))
    if not paths:
        raise FileNotFoundError(f"{model_dir} 下没有 seed*/per_user.parquet")
    return [pd.read_parquet(p, columns=["user_id", "rank"]) for p in paths]


# --------------------------------------------------------------------------- 核心检验
def paired_test_arrays(a: Iterable[float], b: Iterable[float]) -> dict:
    """对两组配对的逐用户指标做 t 检验与 Wilcoxon。

    d_z = t / sqrt(n)，n 为配对数（用户数）。
    """
    a_arr = np.asarray(list(a), dtype=np.float64)
    b_arr = np.asarray(list(b), dtype=np.float64)
    if a_arr.shape != b_arr.shape:
        raise ValueError("配对样本长度不一致")
    n = int(len(a_arr))
    if n == 0:
        raise ValueError("配对样本为空")

    if n < 2:
        raise ValueError("配对检验至少需要 2 个用户")

    diff = a_arr - b_arr
    delta = float(diff.mean())

    t_stat: Optional[float]
    p_t: Optional[float]
    d_z: Optional[float]

    all_zero = bool(np.allclose(diff, 0.0))
    # 所有用户差值完全相同 → 方差为 0，t 与 d_z 无定义，不能写成 inf/nan（JSON 无法序列化）
    degenerate = (not all_zero) and float(np.std(diff, ddof=1)) == 0.0

    if all_zero:
        t_stat, p_t, d_z = 0.0, 1.0, 0.0
    elif degenerate:
        t_stat, p_t, d_z = None, 0.0, None
    else:
        t_res = sps.ttest_rel(a_arr, b_arr)
        t_stat = float(t_res.statistic)
        p_t = float(t_res.pvalue)
        d_z = float(t_stat / math.sqrt(n))

    if all_zero:
        wilcoxon_p = 1.0
    else:
        try:
            wilcoxon_p = float(sps.wilcoxon(a_arr, b_arr).pvalue)
        except ValueError:  # 样本过小等无法计算的情形
            wilcoxon_p = 1.0

    return {
        "n": n,
        "mean_a": float(a_arr.mean()),
        "mean_b": float(b_arr.mean()),
        "delta": delta,
        "t": t_stat,
        "p_t": p_t,
        "d_z": d_z,
        "wilcoxon_p": wilcoxon_p,
        "degenerate": degenerate,
    }


def compare(
    dfs_a: list[pd.DataFrame],
    dfs_b: list[pd.DataFrame],
    k: int = 10,
    metric: str = "Recall",
) -> dict:
    """两模型多 seed 结果 → 逐用户平均 → 配对检验。

    mean_a / mean_b 是逐用户指标（Recall@K 或 NDCG@K）的均值，不是 rank 均值；
    delta = mean_a - mean_b。
    """
    avg_a = _average_over_seeds([d[["user_id", "rank"]] for d in dfs_a])
    avg_b = _average_over_seeds([d[["user_id", "rank"]] for d in dfs_b])

    # user_id 可能是 int 或 str，统一按 str 对齐，避免 .loc 用错键
    map_a = {str(u): float(v) for u, v in avg_a.items()}
    map_b = {str(u): float(v) for u, v in avg_b.items()}
    users_a, users_b = set(map_a), set(map_b)
    common = sorted(users_a & users_b)
    n_dropped = len(users_a ^ users_b)
    if not common:
        raise ValueError("两个模型的用户集合没有交集")

    ranks_a = {u: map_a[u] for u in common}
    ranks_b = {u: map_b[u] for u in common}

    vals_a = rank_to_metric(ranks_a, k, metric)
    vals_b = rank_to_metric(ranks_b, k, metric)

    keys = list(common)
    result = paired_test_arrays([vals_a[u] for u in keys], [vals_b[u] for u in keys])
    result.update(
        {
            "metric": _metric_name(metric, k),
            "k": k,
            "seeds_a": len(dfs_a),
            "seeds_b": len(dfs_b),
            "n_dropped": n_dropped,
        }
    )
    return result


def compare_from_dirs(dir_a: Path, dir_b: Path, k: int = 10, metric: str = "Recall") -> dict:
    return compare(
        _load_per_user_dirs(dir_a),
        _load_per_user_dirs(dir_b),
        k=k,
        metric=metric,
    )


def compare_and_write(*args, out_path: Path, **kwargs) -> dict:
    result = compare(*args, **kwargs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


# --------------------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description="两模型配对检验（以用户为单位）")
    ap.add_argument("--dir-a", type=Path, required=True,
                    help="模型 A 目录，含 seed*/per_user.parquet")
    ap.add_argument("--dir-b", type=Path, required=True,
                    help="模型 B 目录，含 seed*/per_user.parquet")
    ap.add_argument("--k", type=int, default=10, choices=(10, 20))
    ap.add_argument("--metric", default="Recall", choices=("Recall", "NDCG"))
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    res = compare_from_dirs(args.dir_a, args.dir_b, k=args.k, metric=args.metric)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    print(f"{res['metric']}  A={res['mean_a']:.6f}  B={res['mean_b']:.6f}  "
          f"Δ={res['delta']:+.6f}")
    print(f"n={res['n']}  t={res['t']:.4f}  p={res['p_t']:.4g}  "
          f"d_z={res['d_z']:.4f}  Wilcoxon p={res['wilcoxon_p']:.4g}")
    if res["n_dropped"]:
        print(f"⚠️  两模型用户集合不一致，{res['n_dropped']} 个用户未参与配对")
    print(f"→ {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())