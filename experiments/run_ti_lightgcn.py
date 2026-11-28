"""TI-LightGCN 训练与评估（S-recall-main）

在 LightGCN 基础上引入时间感知反馈加权边权，跑主实验 5 seed。

与 run_recall_baseline.py 的主要差异：
1. 使用自定义模型 TILightGCN（而非 RecBole 内置模型）
2. 边权从 data/processed/IS/train.parquet 计算

其余评估流程（全排序打分、屏蔽、per_user、metrics）完全复用。

用法
----
    # 单次 run
    python experiments/run_ti_lightgcn.py --seed 0

    # 冒烟（CPU、少量 epoch）
    python experiments/run_ti_lightgcn.py --seed 0 --epochs 2 --no-gpu --results-dir results/_smoke/ti_lightgcn
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.run import start_run  # noqa: E402
from eval.metrics import ndcg_at_k, recall_at_k  # noqa: E402
from models.ti_lightgcn import TILightGCN  # noqa: E402

CONFIG_PATH = REPO_ROOT / "configs" / "recall" / "ti_lightgcn.yaml"
DATA_PATH = REPO_ROOT / "data" / "recbole"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "IS"

EXP = "ch3_recall/ti_lightgcn"


def load_config(config_path: Path = CONFIG_PATH) -> dict:
    """读 configs/recall/ti_lightgcn.yaml。"""
    with open(config_path, encoding="utf8") as f:
        return yaml.safe_load(f)


def build_config(cfg: dict, seed: int, data_path: Path, use_gpu: bool) -> dict:
    """把配置翻成 RecBole config_dict。"""
    d = {
        "model": "TILightGCN",
        "dataset": "IS",
        "data_path": str(data_path),
        "benchmark_filename": ["train", "val", "test"],
        "eval_args": {
            "split": {"mode": "custom"},
            "group_by": "user",
            "order": "RO",
            "repeat": "none",
        },
        "metrics": ["Recall", "NDCG"],
        "topk": [10, 20],
        "valid_metric": "Recall@10",
        "eval_batch_size": int(os.environ.get("RECALL_EVAL_BATCH_SIZE", 25849 * 256)),
        "stopping_step": int(cfg.get("stopping_step", 20)),
        "seed": int(seed),
        "use_gpu": bool(use_gpu),
        "gpu_id": 0,
        "log_wandb": False,
        "show_progress": False,
        "save_dataset": False,
        "load_col": {"inter": ["user_id", "item_id", "rating", "timestamp"]},
        # TI-LightGCN 专有
        "lambda_": float(cfg.get("lambda_", 0.001)),
        "gamma": float(cfg.get("gamma", 0.0)),
        "theta": int(cfg.get("theta", 10)),
    }
    skip = {"seeds", "stopping_step", "eval_batch_size"}
    for k, v in cfg.items():
        if k in skip:
            continue
        if k not in d:
            d[k] = v
    return d


# --------------------------------------------------------------------------- 打分
def reshape_scores(scores: np.ndarray, n_rows: int, n_items: int) -> np.ndarray:
    arr = np.asarray(scores, dtype=np.float64)
    if arr.ndim == 2:
        return arr
    return arr.reshape(n_rows, n_items)


def build_shield(processed_dir: Path, item_to_col: dict[int, int]) -> dict[int, np.ndarray]:
    train = pd.read_parquet(processed_dir / "train.parquet",
                            columns=["user_idx", "item_idx"])
    val = pd.read_parquet(processed_dir / "val.parquet",
                          columns=["user_idx", "item_idx"])
    pairs = pd.concat([train, val[["user_idx", "item_idx"]]], ignore_index=True)
    pairs["col"] = pairs["item_idx"].map(item_to_col)
    pairs = pairs.dropna(subset=["col"])

    out: dict[int, np.ndarray] = {}
    for u, grp in pairs.groupby("user_idx", sort=False):
        out[int(u)] = np.unique(grp["col"].to_numpy(dtype=np.int64))
    return out


def ranks_for_users(
    scores: np.ndarray,
    users: np.ndarray,
    shield: dict[int, np.ndarray],
    test_by_user: dict[int, list[int]],
    item_to_col: dict[int, int],
) -> pd.DataFrame:
    n_items = scores.shape[1]
    rows = []
    for r, u in enumerate(users):
        u = int(u)
        items = test_by_user.get(u)
        if not items:
            continue

        valid = np.ones(n_items, dtype=bool)
        sh = shield.get(u)
        if sh is not None and len(sh):
            valid[sh] = False
        n_cand = int(valid.sum())
        if n_cand == n_items:
            cand = scores[r]
        else:
            cand = scores[r][valid]

        for i in items:
            col = item_to_col.get(i)
            if col is None:
                raise KeyError(f"测试物品 item_idx={i} 不在 RecBole 物品表中")
            if not valid[col]:
                rank = float(n_cand) + 1
            else:
                test_score = float(scores[r][col])
                n_better = int((cand > test_score).sum())
                n_equal = int((cand == test_score).sum()) - 1
                rank = 1 + n_better + n_equal
            rows.append({"user_id": u, "test_item": i, "rank": rank})

    return pd.DataFrame(rows)


def prepare_conduct(processed_dir: Path, item_to_col: dict[int, int]) -> dict:
    test = pd.read_parquet(processed_dir / "test.parquet",
                           columns=["user_idx", "item_idx"])
    test_by_user: dict[int, list[int]] = {}
    for u, i in zip(test["user_idx"].astype(int), test["item_idx"].astype(int)):
        test_by_user.setdefault(int(u), []).append(int(i))
    return {
        "shield": build_shield(processed_dir, item_to_col),
        "test_by_user": test_by_user,
        "item_to_col": item_to_col,
    }


def compute_metrics(per_user: pd.DataFrame, ks: tuple[int, ...] = (10, 20)) -> dict:
    ranks = {str(r.user_id): float(r.rank) for r in per_user.itertuples()}
    out = {}
    for k in ks:
        out[f"Recall@{k}"] = recall_at_k(ranks, k)
        out[f"NDCG@{k}"] = ndcg_at_k(ranks, k)
    return out


def per_user_from_model(model, test_data, dataset, conduct, user_to_col) -> pd.DataFrame:
    import torch

    n_items = int(dataset.item_num)
    inv = {v: k for k, v in user_to_col.items()}
    item_to_col = conduct["item_to_col"]
    shield = conduct["shield"]
    test_by_user = conduct["test_by_user"]

    device = next(model.parameters()).device
    model.eval()
    dfs = []
    n_users_total = 0
    with torch.no_grad():
        for user_df, _history, _pos_u, _pos_i in test_data:
            user_df = user_df.to(device)
            out = model.full_sort_predict(user_df)
            internal_users = user_df[dataset.uid_field].detach().cpu().numpy().astype(int)
            block = reshape_scores(out.detach().cpu().numpy(), len(internal_users), n_items)
            users = np.array([inv[int(u)] for u in internal_users], dtype=np.int64)

            dfs.append(ranks_for_users(block, users, shield, test_by_user, item_to_col))
            n_users_total += len(users)

    per_user = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(
        columns=["user_id", "test_item", "rank"])
    print(f"  [打分] {len(dfs)} 批 / {n_users_total} 用户 → {len(per_user)} 行")
    return per_user


def _token_to_internal(dataset, field: str) -> dict[int, int]:
    out = {}
    for token, internal in dataset.field2token_id[field].items():
        try:
            out[int(token)] = int(internal)
        except ValueError:
            continue
    return out


# --------------------------------------------------------------------------- 训练
def train_and_eval(
    cfg: dict,
    seed: int,
    data_path: Path,
    use_gpu: bool,
    epochs: int | None = None,
):
    """跑完一个 run，返回 (metrics, per_user, info)。"""
    import torch
    from recbole.config import Config
    from recbole.data import create_dataset, data_preparation
    from recbole.utils import get_trainer, init_seed, ModelType

    config_dict = build_config(cfg, seed, data_path, use_gpu)
    if epochs is not None:
        config_dict["epochs"] = int(epochs)

    # 注册自定义模型
    import recbole.utils as _recbole_utils
    _orig_get_model = _recbole_utils.get_model
    def _patched_get_model(model_name):
        if model_name == "TILightGCN":
            return TILightGCN
        try:
            return _orig_get_model(model_name)
        except ValueError:
            raise ValueError(f"未知模型: {model_name}")
    _recbole_utils.get_model = _patched_get_model
    import recbole.config.configurator as _cfg_mod
    _cfg_mod.get_model = _patched_get_model

    config = Config(model="TILightGCN", dataset="IS", config_dict=config_dict)
    init_seed(config["seed"], config["reproducibility"])

    # 图构建耗时
    t_build = time.time()
    dataset = create_dataset(config)
    train_data, valid_data, test_data = data_preparation(config, dataset)

    model = TILightGCN(config, train_data.dataset).to(config["device"])
    t_build = time.time() - t_build

    trainer_class = get_trainer(ModelType.GENERAL, config["model"])
    trainer = trainer_class(config, model)

    # ---- 训练过程度量（表3-15 / 图3-9）----
    epoch_stats: list[dict] = []
    best_epoch_box = [-1]

    def _loss_with_batch_size(loss_func):
        def wrapped(interaction):
            if epoch_stats:
                epoch_stats[-1]["n_batches"] += 1
            return loss_func(interaction)
        return wrapped

    _orig_calc_loss = model.calculate_loss
    model.calculate_loss = _loss_with_batch_size(_orig_calc_loss)

    _orig_train_epoch = trainer._train_epoch

    def _timed_train_epoch(*args, **kwargs):
        epoch_stats.append({"seconds": 0.0, "loss_sum": 0.0, "n_batches": 0})
        t0 = time.time()
        raw = _orig_train_epoch(*args, **kwargs)
        dt = time.time() - t0

        if isinstance(raw, tuple):
            total, _ = raw
            loss_sum = float(sum(total)) if isinstance(total, tuple) else float(total)
        else:
            loss_sum = float(raw)
        epoch_stats[-1]["seconds"] = dt
        epoch_stats[-1]["loss_sum"] = loss_sum
        return raw

    trainer._train_epoch = _timed_train_epoch

    def _on_epoch(epoch_idx, valid_score):
        best_epoch_box[0] = epoch_idx
        if epoch_stats:
            epoch_stats[-1]["epoch"] = int(epoch_idx)
            epoch_stats[-1]["valid_score"] = float(valid_score)

    t_fit = time.time()
    trainer.fit(train_data, valid_data, saved=True,
                show_progress=config["show_progress"], callback_fn=_on_epoch)
    fit_seconds = time.time() - t_fit

    model.calculate_loss = _orig_calc_loss
    trainer._train_epoch = _orig_train_epoch

    # 峰值显存
    peak_mem_mb = None
    if use_gpu and torch.cuda.is_available():
        peak_mem_mb = float(torch.cuda.max_memory_allocated()) / 2 ** 20

    best_epoch = best_epoch_box[0]
    if trainer.saved_model_file and Path(trainer.saved_model_file).exists():
        state = torch.load(trainer.saved_model_file, map_location=config["device"])
        best_epoch = int(state["epoch"])
        model.load_state_dict(state["state_dict"])
        model.load_other_parameter(state.get("other_parameter"))
        model.eval()
    else:
        raise RuntimeError("没有生成 checkpoint")

    # 测试集评估
    recbole_result = trainer.evaluate(test_data, load_best_model=False, show_progress=False)
    recbole_metrics = {
        f"recbole_{k}": float(v) for k, v in recbole_result.items()
        if isinstance(v, (int, float))
    }

    user_to_col = _token_to_internal(dataset, dataset.uid_field)
    item_to_col = _token_to_internal(dataset, dataset.iid_field)

    conduct = prepare_conduct(PROCESSED_DIR, item_to_col)
    per_user = per_user_from_model(model, test_data, dataset, conduct, user_to_col)

    metrics = compute_metrics(per_user)
    metrics.update(recbole_metrics)

    info = {
        "best_valid_score": float(trainer.best_valid_score),
        "best_epoch": int(best_epoch),
        "train_loss": {int(k): float(v) for k, v in trainer.train_loss_dict.items()},
        "recbole_metrics": recbole_metrics,
        "user_id_mapped": len(user_to_col),
        "item_id_mapped": len(item_to_col),
        "user_num": int(dataset.user_num),
        "item_num": int(dataset.item_num),
        "epoch_stats": epoch_stats,
        "build_seconds": float(t_build),
        "fit_seconds": float(fit_seconds),
        "peak_mem_mb": peak_mem_mb,
        "n_params": int(sum(p.numel() for p in model.parameters() if p.requires_grad)),
    }
    return metrics, per_user, info


# --------------------------------------------------------------------------- 入口
def main() -> int:
    ap = argparse.ArgumentParser(description="TI-LightGCN 训练与评估（S-recall-main）")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--data-path", type=Path, default=DATA_PATH)
    ap.add_argument("--config-path", type=Path, default=CONFIG_PATH)
    ap.add_argument("--no-gpu", action="store_true")
    ap.add_argument("--results-dir", type=Path, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config_path)
    use_gpu = not args.no_gpu

    with start_run(EXP, "ti_lightgcn", args.seed,
                   config={**cfg, "recbole_config": build_config(cfg, args.seed,
                                                                 args.data_path, use_gpu)},
                   results_dir=args.results_dir) as h:
        t0 = time.time()
        metrics, per_user, info = train_and_eval(
            cfg, args.seed, args.data_path, use_gpu, epochs=args.epochs
        )
        elapsed = time.time() - t0

        h.write_metrics(metrics)
        per_user.to_parquet(h.dir / "per_user.parquet", index=False)

        for st in info["epoch_stats"]:
            n_batches = st.get("n_batches") or 0
            loss = (st["loss_sum"] / n_batches) if n_batches else None
            h.log_epoch(
                epoch=st.get("epoch", -1),
                loss=loss,
                seconds=st.get("seconds"),
                n_eval=st.get("valid_score"),
            )
        logged = {st.get("epoch") for st in info["epoch_stats"]}
        for epoch, loss in info["train_loss"].items():
            if epoch not in logged:
                h.log_epoch(epoch=epoch, loss=loss)

        if info["best_epoch"] is not None:
            h.set_best_epoch(info["best_epoch"])
        if info["peak_mem_mb"] is not None:
            h.set_peak_memory(info["peak_mem_mb"])
        h.set_stop_reason("patience")
        h.write_manifest(extra={
            "elapsed_s": round(elapsed, 1),
            "epochs": args.epochs or cfg.get("epochs"),
            "recbole_metrics": info["recbole_metrics"],
            "best_valid_score": info["best_valid_score"],
            "build_seconds": round(info["build_seconds"], 2),
            "fit_seconds": round(info["fit_seconds"], 2),
            "peak_memory_mb": info["peak_mem_mb"],
            "n_params": info["n_params"],
            "n_epochs_logged": len(info["epoch_stats"]),
            "user_id_mapped": info["user_id_mapped"],
            "item_id_mapped": info["item_id_mapped"],
            "user_num": info["user_num"],
            "item_num": info["item_num"],
            "dataset": "IS",
            "data_scope": "train",
            # TI-LightGCN 专有
            "lambda_": cfg.get("lambda_"),
            "gamma": cfg.get("gamma"),
            "theta": cfg.get("theta"),
        })

        print(f"[ti_lightgcn/seed{args.seed}] " + "  ".join(
            f"{k}={v:.4f}" for k, v in metrics.items() if not k.startswith("recbole_")))
        print(f"→ {h.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
