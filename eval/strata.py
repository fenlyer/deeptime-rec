"""冷启动分层（S1-c）

按训练集交互数把用户分到固定的五层，逐层报告指标，并做守恒校验。

口径
----
    - 分层依据是「训练集交互数」，只用 train 的行数，不含验证/测试交互
      （G4 不过时的原因就是有人用了含测试的交互数，层间人数对不上）。
    - 层边界：1-2 / 3-4 / 5-9 / 10-29 / >=30。1-2 层是补的冷启动层：
      IS/OP/TH 的 min 都是 3，这一层为空；跨域子采样（data-v1-sub）可能出现。
    - 守恒：Σ(n_i · metric_i) / Σ n_i 必须等于整体 metric（差 < 1e-9）。
      若不等，说明有的用户没被分到层里，或者指标不是逐用户可加的。
    - per_user 中出现但 train 中没有的用户 → 报错停下。静默丢弃会让守恒
      检验失去意义，也会掩盖切分口径不一致的问题。

用法：
    python -m eval.strata \
        --per-user results/recall_main/ti_lightgcn/seed0/per_user.parquet \
        --train data/processed/IS/train.parquet \
        --ks 10 20 --output results/strata/recall_ti.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from eval.metrics import ndcg_at_k, recall_at_k

# 层定义 (名称, 下界含, 上界含)；上界 None 表示无上限
LAYERS: list[tuple[str, int, Optional[int]]] = [
    ("1-2", 1, 2),
    ("3-4", 3, 4),
    ("5-9", 5, 9),
    ("10-29", 10, 29),
    (">=30", 30, None),
]


def assign_layer(count: int) -> str:
    for name, lo, hi in LAYERS:
        if count >= lo and (hi is None or count <= hi):
            return name
    raise ValueError(f"训练集交互数 {count} 不在任何层内（最小层下界为 1）")


def _normalize_ks(ks: Iterable[int]) -> tuple[int, ...]:
    out = tuple(sorted({int(k) for k in ks}))
    if not out:
        raise ValueError("ks 不能为空")
    return out


def compute_strata(
    per_user: pd.DataFrame,
    train: pd.DataFrame,
    ks: Iterable[int] = (10, 20),
) -> dict:
    """per_user（user_id, rank）与 train（user_id, ...）→ 分层指标。

    返回结构：见模块 docstring 与 JSON 输出。
    """
    ks = _normalize_ks(ks)
    if per_user.empty:
        raise ValueError("per_user 为空，无法分层")

    counts = train.groupby("user_id").size()
    pu = per_user.copy()
    pu["user_id"] = pu["user_id"].astype(str)

    missing = sorted(set(pu["user_id"]) - set(counts.index.astype(str)))
    if missing:
        raise KeyError(
            f"per_user 中有 {len(missing)} 个用户不在训练集中（例：{missing[0]}）。"
            "切分口径可能不一致，拒绝静默丢弃。"
        )

    counts.index = counts.index.astype(str)
    pu["train_pairs"] = pu["user_id"].map(counts)
    pu["layer"] = pu["train_pairs"].map(assign_layer)

    ranks = dict(zip(pu["user_id"], pu["rank"].astype(float)))

    overall = {}
    for k in ks:
        overall[f"Recall@{k}"] = recall_at_k(ranks, k)
        overall[f"NDCG@{k}"] = ndcg_at_k(ranks, k)

    layers: dict[str, dict] = {}
    for name, _, _ in LAYERS:
        sub = pu[pu["layer"] == name]
        n = int(len(sub))
        if n == 0:
            layers[name] = {
                "n": 0,
                "range": _range_label(name),
                "metrics": {f"{m}@{k}": None for k in ks for m in ("Recall", "NDCG")},
            }
            continue
        sub_ranks = dict(zip(sub["user_id"], sub["rank"].astype(float)))
        metrics = {}
        for k in ks:
            metrics[f"Recall@{k}"] = recall_at_k(sub_ranks, k)
            metrics[f"NDCG@{k}"] = ndcg_at_k(sub_ranks, k)
        layers[name] = {
            "n": n,
            "range": _range_label(name),
            "train_pairs_median": float(sub["train_pairs"].median()),
            "metrics": metrics,
        }

    return {
        "ks": list(ks),
        "n": int(len(pu)),
        "overall": overall,
        "layers": layers,
        "layer_order": [name for name, _, _ in LAYERS],
    }


def _range_label(name: str) -> str:
    for n, lo, hi in LAYERS:
        if n == name:
            return f"{lo}-{hi}" if hi is not None else f">={lo}"
    return name


def assert_conservation(result: dict, tol: float = 1e-9) -> None:
    """按人数加权的层均值必须等于整体指标。"""
    layers = result["layers"]
    n_total = sum(v["n"] for v in layers.values())
    if n_total != result["n"]:
        raise AssertionError(
            f"分层人数之和 {n_total} ≠ 用户总数 {result['n']}，有用户未落层"
        )
    non_empty = [v for v in layers.values() if v["n"] > 0]
    if not non_empty:
        raise AssertionError("所有层都为空")

    for metric_key in result["overall"]:
        weighted = sum(v["n"] * v["metrics"][metric_key] for v in non_empty) / n_total
        overall = result["overall"][metric_key]
        if abs(weighted - overall) > tol:
            raise AssertionError(
                f"{metric_key} 守恒失败：加权 {weighted!r} vs 整体 {overall!r}"
                f"（差 {abs(weighted - overall):.3e} > {tol:g}）"
            )


def compute_strata_from_files(
    per_user_path: Path,
    train_path: Path,
    ks: Iterable[int] = (10, 20),
) -> dict:
    per_user = pd.read_parquet(per_user_path, columns=["user_id", "rank"])
    train = pd.read_parquet(train_path, columns=["user_id"])
    result = compute_strata(per_user, train, ks=ks)
    assert_conservation(result)
    return result


# --------------------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description="冷启动分层（训练集口径）与守恒校验")
    ap.add_argument("--per-user", type=Path, required=True)
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--ks", type=int, nargs="+", default=[10, 20])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    result = compute_strata_from_files(args.per_user, args.train, ks=args.ks)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"用户数 {result['n']:,}")
    for name in result["layer_order"]:
        v = result["layers"][name]
        if v["n"] == 0:
            print(f"  {name:>6}  n=0")
            continue
        r10 = v["metrics"]["Recall@10"]
        print(f"  {name:>6}  n={v['n']:>6}  Recall@10={r10:.4f}")
    print(f"  整体      n={result['n']:>6}  "
          f"Recall@10={result['overall']['Recall@10']:.4f}")
    print("✅ 守恒校验通过")
    print(f"→ {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())