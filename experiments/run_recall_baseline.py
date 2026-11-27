"""召回基线训练与评估（S-recall-base）

用 RecBole 在冻结切分（data/recbole/IS/{train,val,test}.inter）上训练召回基线，
打分后用 eval/ 的口径重算指标，结果落 results/ch3_recall/baselines/{model}/seed{n}/。

口径
----
    - 切分：benchmark_filename 加载冻结 train/val/test，禁用 RecBole 内部切分与过滤。
    - 早停：验证集 Recall@10（valid_metric），patience = stopping_step = 20，
      最多 epochs = 200。测试集只在训练结束后读一次。
    - 数字来源：metrics.json 里的 Recall@10/20、NDCG@10/20 由 eval/full_rank.py 的
      悲观并列 + 屏蔽训练∩验证口径算出，与主模型（TI-LightGCN）可比。
      RecBole 原生评估另存 recbole_{metric} 字段，只做对账，不进论文。
    - 打分：对测试集每行 (user, item) 调 model.full_sort_predict，取全物品打分矩阵。

用法
----
    # 单次 run
    python experiments/run_recall_baseline.py --model lightgcn --seed 0

    # 冒烟（CPU、少量 epoch、落 results/_smoke/）
    python experiments/run_recall_baseline.py --model bprmf --seed 0 \
        --epochs 2 --no-gpu --results-dir results/_smoke/recall

    # 汇总 25 个 run
    python experiments/make_baseline_summary.py
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.run import start_run  # noqa: E402
from eval.metrics import ndcg_at_k, recall_at_k  # noqa: E402

CONFIG_DIR = REPO_ROOT / "configs" / "recall"
DATA_PATH = REPO_ROOT / "data" / "recbole"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "IS"

# 配置文件名 → RecBole 模型类名
RECBOLE_MODEL = {
    "bprmf": "BPR",
    "ngcf": "NGCF",
    "lightgcn": "LightGCN",
    "sgl": "SGL",
    "simgcl": "SimGCL",
}

EXP = "ch3_recall/baselines"


# --------------------------------------------------------------------------- 配置
def load_model_config(model_key: str, config_dir: Path = CONFIG_DIR) -> dict:
    """读 configs/recall/{model_key}.yaml。"""
    path = Path(config_dir) / f"{model_key}.yaml"
    with open(path, encoding="utf8") as f:
        cfg = yaml.safe_load(f)
    if model_key not in RECBOLE_MODEL:
        raise KeyError(f"未知模型 {model_key}，可选 {sorted(RECBOLE_MODEL)}")
    return cfg


def build_config(
    model_key: str, cfg: dict, seed: int, data_path: Path, use_gpu: bool
) -> dict:
    """把卡片配置翻成 RecBole config_dict（不改源 dict）。

    cfg 里除 seeds 外的标量/列表项（embedding_size、n_layers、cl_loss 等）原样透传，
    这样每个模型的超参只需要在 yaml 里写一次。
    """
    d = {
        "model": RECBOLE_MODEL[model_key],
        "dataset": "IS",
        "data_path": str(data_path),
        "benchmark_filename": ["train", "val", "test"],
        # 冻结切分：不做 RecBole 内部切分
        "eval_args": {
            "split": {"mode": "custom"},
            "group_by": "user",
            "order": "RO",
            "repeat": "none",
        },
        "metrics": ["Recall", "NDCG"],
        "topk": [10, 20],
        "valid_metric": "Recall@10",
        # RecBole 全排序评估每批用户数 = eval_batch_size // item_num。
        # 物品 25849，设 4096 会使每批只有 1 个用户（50985 批）；这里按
        # 「约 256 用户/批」取 25849*256，显著减少批次数与 Python 循环开销。
        "eval_batch_size": int(os.environ.get("RECALL_EVAL_BATCH_SIZE", 25849 * 256)),
        # 早停耐心在 RecBole 里叫 stopping_step
        "stopping_step": int(cfg.get("stopping_step", cfg.get("early_stop", 20))),
        "seed": int(seed),
        "use_gpu": bool(use_gpu),
        "gpu_id": 0,
        "log_wandb": False,
        "show_progress": False,
        "save_dataset": False,
        "load_col": {"inter": ["user_id", "item_id", "rating", "timestamp"]},
    }
    # 透传模型超参与训练参数，跳过卡片自己的字段与由本函数计算的字段
    skip = {"seeds", "stopping_step", "early_stop", "eval_batch_size"}
    for k, v in cfg.items():
        if k in skip:
            continue
        d[k] = v
    return d


# --------------------------------------------------------------------------- 打分
def reshape_scores(scores: np.ndarray, n_rows: int, n_items: int) -> np.ndarray:
    """full_sort_predict 的返回值统一成 (n_rows, n_items)。

    BPR / NGCF / LightGCN / SGL 的 full_sort_predict 返回扁平数组，
    个别实现可能已 reshape；两种都接受。
    """
    arr = np.asarray(scores, dtype=np.float64)
    if arr.ndim == 2:
        return arr
    return arr.reshape(n_rows, n_items)


def build_shield(processed_dir: Path, item_to_col: dict[int, int]) -> dict[int, np.ndarray]:
    """预计算每个用户的屏蔽列号（训练集 ∩ 验证集物品）。

    必须在这里一次算完：若放进批循环内，每批都要重扫 36 万行，
    而 RecBole 的 eval_batch_size 小于物品数时每批只有 1 个用户 —— 会慢到不可用。
    """
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
    """给定若干用户的打分行，算这些用户的 per_user 行（user_id / test_item / rank）。

    与 eval/full_rank.py 同口径：
        - 候选 = 全部物品 − 该用户在训练集与验证集中的物品
        - 并列取悲观排名：rank = 1 + (比它高分的候选数) + (与它同分的候选数)
        - 测试物品被屏蔽（出现在训练/验证集）→ rank = 候选数 + 1（不可达，排最后）

    参数
    ----
    scores : (len(users), n_items) 打分块，列是 RecBole 内部编号
    users : (len(users),) 对应的 processed user_idx
    shield : build_shield 的结果（每用户屏蔽列号）
    test_by_user : {user_idx: [item_idx, ...]}，每个用户的测试物品
    """
    n_items = scores.shape[1]
    rows = []
    for r, u in enumerate(users):
        u = int(u)
        items = test_by_user.get(u)
        if not items:
            continue  # 该用户没有测试行（出现则说明切分不一致）

        valid = np.ones(n_items, dtype=bool)
        sh = shield.get(u)
        if sh is not None and len(sh):
            valid[sh] = False
        n_cand = int(valid.sum())
        if n_cand == n_items:
            cand = scores[r]          # 无屏蔽时避免多一次拷贝
        else:
            cand = scores[r][valid]

        for i in items:
            col = item_to_col.get(i)
            if col is None:
                raise KeyError(f"测试物品 item_idx={i} 不在 RecBole 物品表中")
            if not valid[col]:
                rank = float(n_cand) + 1  # 测试物品在训练/验证里 → 不可达
            else:
                test_score = float(scores[r][col])
                n_better = int((cand > test_score).sum())
                n_equal = int((cand == test_score).sum()) - 1  # 减掉测试物品自身
                rank = 1 + n_better + n_equal
            rows.append({"user_id": u, "test_item": i, "rank": rank})

    return pd.DataFrame(rows)


def scores_to_per_user(
    scores: np.ndarray,
    conduct: dict,
) -> pd.DataFrame:
    """全量打分矩阵 → per_user。conduct 由 prepare_conduct 给出。"""
    users = np.arange(scores.shape[0])
    return ranks_for_users(scores, users, conduct["shield"],
                           conduct["test_by_user"], conduct["item_to_col"])


def prepare_conduct(processed_dir: Path, item_to_col: dict[int, int]) -> dict:
    """一次性预计算 per_user 所需的全部索引（屏蔽集 + 测试物品索引）。"""
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
    """per_user → {Recall@K, NDCG@K}，与 eval/metrics.py 一致（LOO、IDCG=1）。"""
    ranks = {str(r.user_id): float(r.rank) for r in per_user.itertuples()}
    out = {}
    for k in ks:
        out[f"Recall@{k}"] = recall_at_k(ranks, k)
        out[f"NDCG@{k}"] = ndcg_at_k(ranks, k)
    return out


# --------------------------------------------------------------------------- 训练
def _token_to_internal(dataset, field: str) -> dict[int, int]:
    """field2token_id（token 字符串 → RecBole 内部编号）→ {processed idx: 内部编号}。

    内部编号里 [PAD]=0，与 processed 的 user_idx/item_idx 错开 1 位；
    不用固定 offset，避免 RecBole 版本差异导致错列。
    """
    out = {}
    for token, internal in dataset.field2token_id[field].items():
        try:
            out[int(token)] = int(internal)
        except ValueError:
            continue  # [PAD] 等特殊 token
    return out


def per_user_from_model(
    model, test_data, dataset, conduct, user_to_col
) -> pd.DataFrame:
    """直接在评估 DataLoader 上算 per_user，不保存全物品打分矩阵。

    全量矩阵是 (50986, 25849) float64 ≈ 10.5 GB。改成按批算：每批只保留一个
    (batch_users, n_items) 块，算完该批的 rank 就丢掉。屏蔽集与测试索引由
    prepare_conduct 一次性预计算好，批内只做排名。
    """
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


def train_and_eval(
    model_key: str,
    cfg: dict,
    seed: int,
    data_path: Path,
    use_gpu: bool,
    epochs: int | None = None,
):
    """跑完一个 run，返回 (metrics, per_user, 对账信息)。"""
    import time

    import torch

    from recbole.config import Config
    from recbole.utils import get_trainer, init_seed, ModelType

    # RecBole-GNN 按需加载：装了它就用它的 create_dataset/data_preparation
    # （会优先查 GNN 数据集，查不到再 fallback 到 RecBole 原生）；没装则用原生。
    # 这样 BPR 这类纯 RecBole 模型在没有 recbole_gnn 的环境里也能跑。
    try:
        from recbole_gnn.utils import create_dataset, data_preparation
        import recbole_gnn.utils as _gnn_utils
    except ModuleNotFoundError:
        from recbole.data import create_dataset, data_preparation
        _gnn_utils = None

    # monkey-patch recbole.utils.get_model，让 Config 内部能查到 RecBole-GNN 模型
    # （SimGCL/SGL/NGCF/LightGCN）。RecBole Config 在 __init__ 时调 recbole.utils.get_model。
    import recbole.utils as _recbole_utils
    _orig_get_model = _recbole_utils.get_model
    def _patched_get_model(model_name):
        try:
            return _orig_get_model(model_name)
        except ValueError:
            if _gnn_utils is None:
                raise
            return _gnn_utils.get_model(model_name)
    _recbole_utils.get_model = _patched_get_model
    # Config 内部 from recbole.utils import get_model，需要也 patch 到 configurator 模块
    import recbole.config.configurator as _cfg_mod
    _cfg_mod.get_model = _patched_get_model

    config_dict = build_config(model_key, cfg, seed, data_path, use_gpu)
    if epochs is not None:
        config_dict["epochs"] = int(epochs)

    config = Config(model=config_dict["model"], dataset="IS", config_dict=config_dict)
    init_seed(config["seed"], config["reproducibility"])

    # 图构建/数据准备耗时：数据集加载 + 模型构造（含加权邻接矩阵与归一化预计算）
    t_build = time.time()
    dataset = create_dataset(config)
    train_data, valid_data, test_data = data_preparation(config, dataset)

    model_class = _patched_get_model(config["model"])
    model = model_class(config, train_data.dataset).to(config["device"])
    t_build = time.time() - t_build

    trainer_class = get_trainer(ModelType.GENERAL, config["model"])
    trainer = trainer_class(config, model)

    # ---- 训练过程度量（表3-15 / 图3-9）-----------------------------------
    # 两个 hook 各管一件事：
    #   1) 包装 _train_epoch：用前后时间差拿**纯训练**耗时（不含验证），并累积真实损失。
    #      不能直接用 trainer.train_loss_dict：它累加的是各批 mean loss
    #      （≈ 批次数 × ln2 = 105.358372，与批大小无关，BPR/LightGCN 完全相同），
    #      不能当训练曲线。这里改成逐批 loss × len(interaction) 求和再除样本数。
    #   2) callback_fn：拿每 epoch 的验证 valid_metric（Recall@10）。
    epoch_stats: list[dict] = []
    best_epoch_box = [-1]

    def _loss_with_batch_size(loss_func):
        """包一层：只统计本 epoch 的批数。

        注意：RecBole 的 model.calculate_loss 返回的是**批内 mean**，
        _train_epoch 累加得到「mean 之和」，所以样本均值损失 = loss_sum / 批次数。
        不按样本数归一（按样本数除会得到 mean/2048，无意义）。
        """
        def wrapped(interaction):
            if epoch_stats:
                epoch_stats[-1]["n_batches"] += 1
            return loss_func(interaction)
        return wrapped

    # fit() 调 _train_epoch 时不传 loss_func（默认 None → 用 model.calculate_loss），
    # 所以在 _timed_train_epoch 里包 args/kwargs 两条路都覆盖不到。直接从源头包装模型方法。
    _orig_calc_loss = model.calculate_loss
    model.calculate_loss = _loss_with_batch_size(_orig_calc_loss)

    _orig_train_epoch = trainer._train_epoch

    def _timed_train_epoch(*args, **kwargs):
        # 先占一个槽位，供 loss 包装函数累加批数与样本数
        epoch_stats.append({"seconds": 0.0, "loss_sum": 0.0, "n_batches": 0})
        t0 = time.time()
        raw = _orig_train_epoch(*args, **kwargs)
        dt = time.time() - t0

        if isinstance(raw, tuple):
            total, _ = raw
            # 多分量损失：total 是逐分量之和的 tuple（SGL/SimGCL 会这样返回）
            loss_sum = float(sum(total)) if isinstance(total, tuple) else float(total)
        else:
            loss_sum = float(raw)
        # 写回已占的槽位（n_samples 由 loss 包装函数累加，这里不覆盖）
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

    # 还原被包装的 calculate_loss，避免影响后续 evaluate / 打分
    model.calculate_loss = _orig_calc_loss
    trainer._train_epoch = _orig_train_epoch

    # 峰值显存：仅 GPU 有效；CPU 冒烟为 None
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
        raise RuntimeError("没有生成 checkpoint，无法保证用的是验证集最优 epoch")

    # 测试集只读一次：RecBole 原生评估留作对账
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
        # ---- 训练过程度量（表3-15 / 图3-9）
        "epoch_stats": epoch_stats,
        "build_seconds": float(t_build),
        "fit_seconds": float(fit_seconds),
        "peak_mem_mb": peak_mem_mb,
        "n_params": int(sum(p.numel() for p in model.parameters() if p.requires_grad)),
    }
    return metrics, per_user, info


# --------------------------------------------------------------------------- summary
def collect_summary_rows(baselines_dir: Path) -> list[dict]:
    """读 {model}/seed{n}/metrics.json → [{model, metric, mean, std, n_seeds}]。"""
    baselines_dir = Path(baselines_dir)
    rows: list[dict] = []
    if not baselines_dir.is_dir():
        return rows

    for model_dir in sorted(p for p in baselines_dir.iterdir() if p.is_dir()):
        per_metric: dict[str, list[float]] = {}
        for seed_dir in sorted(model_dir.glob("seed*")):
            metrics_path = seed_dir / "metrics.json"
            if not metrics_path.exists():
                continue
            mf = seed_dir / "manifest.json"
            if mf.exists():
                try:
                    if json.loads(mf.read_text(encoding="utf8")).get("git_dirty"):
                        continue
                except (json.JSONDecodeError, OSError):
                    pass
            data = json.loads(metrics_path.read_text(encoding="utf8"))
            for k, v in data.items():
                if k.startswith("recbole_"):
                    continue
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    per_metric.setdefault(k, []).append(float(v))
        for metric in sorted(per_metric):
            values = per_metric[metric]
            rows.append({
                "model": model_dir.name,
                "metric": metric,
                "mean": statistics.fmean(values),
                "std": statistics.stdev(values) if len(values) > 1 else None,
                "n_seeds": len(values),
            })
    return rows


# --------------------------------------------------------------------------- 入口
def main() -> int:
    ap = argparse.ArgumentParser(description="召回基线训练与评估（S-recall-base）")
    ap.add_argument("--model", required=True, choices=sorted(RECBOLE_MODEL))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=None, help="覆盖配置里的 epochs（冒烟用）")
    ap.add_argument("--data-path", type=Path, default=DATA_PATH)
    ap.add_argument("--config-dir", type=Path, default=CONFIG_DIR)
    ap.add_argument("--no-gpu", action="store_true")
    ap.add_argument("--results-dir", type=Path, default=None,
                    help="覆盖 results/ 根目录（默认 results/；冒烟传 results/_smoke/recall）")
    args = ap.parse_args()

    cfg = load_model_config(args.model, args.config_dir)
    use_gpu = not args.no_gpu

    with start_run(EXP, args.model, args.seed,
                   config={**cfg, "recbole_config": build_config(args.model, cfg, args.seed,
                                                                 args.data_path, use_gpu)},
                   results_dir=args.results_dir) as h:
        import time
        t0 = time.time()
        metrics, per_user, info = train_and_eval(
            args.model, cfg, args.seed, args.data_path, use_gpu, epochs=args.epochs
        )
        elapsed = time.time() - t0

        h.write_metrics(metrics)
        per_user.to_parquet(h.dir / "per_user.parquet", index=False)

        # 逐 epoch：样本均值损失（loss_sum / 批次数）+ 纯训练耗时 + 验证 Recall@10。
        # 口径：RecBole 的 calculate_loss 返回批内 mean，_train_epoch 累加得 mean 之和，
        # 故除以批次数即得该 epoch 的平均批损失。seconds 不含验证评估。
        for st in info["epoch_stats"]:
            n_batches = st.get("n_batches") or 0
            loss = (st["loss_sum"] / n_batches) if n_batches else None
            h.log_epoch(
                epoch=st.get("epoch", -1),
                loss=loss,
                seconds=st.get("seconds"),
                n_eval=st.get("valid_score"),
            )
        # 没有 callback 记录的 epoch（理论上不发生）用 REC 损失兜底，保证行数 == 训练轮数
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
            # ---- 训练过程度量（表3-15 / 图3-9）
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
        })

        print(f"[{args.model}/seed{args.seed}] " + "  ".join(
            f"{k}={v:.4f}" for k, v in metrics.items() if not k.startswith("recbole_")))
        print(f"→ {h.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())