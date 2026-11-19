"""LightGCN smoke 训练（S1-b）

用 RecBole 在冻结切分上训练 LightGCN。
本机 CPU 可跑通数据加载，但全排序评估太慢；正式训练在 AutoDL GPU 上跑。

使用
----
    # AutoDL GPU（推荐）
    conda activate rec
    python experiments/recbole_smoke.py --epochs 50

    # 本机 CPU（仅验证数据加载）
    python experiments/recbole_smoke.py --epochs 5 --no-gpu

输出
----
    results/_smoke/recbole/
        LightGCN-<timestamp>.pth   # checkpoint
        recbole_metrics.json       # 评估指标
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_smoke(data_path: Path, output_dir: Path, epochs: int = 10, use_gpu: bool = True):
    """运行 LightGCN smoke 训练。"""
    # 导入 RecBole
    try:
        from recbole.config import Config
        from recbole.data import create_dataset, data_preparation
        from recbole.utils import init_seed, get_model, get_trainer, ModelType
    except ImportError as e:
        print(f"RecBole 未安装: {e}")
        print("请安装 RecBole：pip install recbole")
        sys.exit(1)

    # 自动检测 GPU
    if use_gpu and not torch.cuda.is_available():
        print("警告：指定使用 GPU 但 CUDA 不可用，回退到 CPU")
        use_gpu = False

    device_name = "cuda" if use_gpu else "cpu"
    print(f"使用设备: {device_name}")

    # 配置
    config_dict = {
        # 数据集
        "dataset": "IS",
        "data_path": str(data_path),
        "benchmark_filename": ["train", "val", "test"],

        # 评估设置
        "eval_args": {
            "split": {"mode": "custom"},
            "group_by": "user",
            "order": "RO",
            "repeat": "none",
        },

        # 评估指标
        "metrics": ["Recall", "NDCG"],
        "topk": [10, 20],
        "valid_metric": "Recall@10",

        # LightGCN 参数
        "model": "LightGCN",
        "embedding_size": 64,
        "n_layers": 3,

        # 训练参数
        "epochs": epochs,
        "train_batch_size": 2048,
        "eval_batch_size": 4096,
        "eval_step": 1,
        "learner": "adam",
        "learning_rate": 0.001,
        "weight_decay": 1e-4,
        "early_stop": 10,

        # 设备
        "use_gpu": use_gpu,
        "gpu_id": 0,

        # 随机种子
        "seed": 0,

        # 日志与保存
        "log_wandb": False,
        "checkpoint_dir": str(output_dir),

        # 加载列
        "load_col": {"inter": ["user_id", "item_id", "rating", "timestamp"]},
    }

    print("初始化配置...")
    config = Config(model="LightGCN", dataset="IS", config_dict=config_dict)
    init_seed(config["seed"], config["reproducibility"])

    print("加载数据集...")
    dataset = create_dataset(config)
    print(f"  用户数: {dataset.user_num}")
    print(f"  物品数: {dataset.item_num}")

    print("准备数据...")
    train_data, valid_data, test_data = data_preparation(config, dataset)
    print(f"  训练集: {len(train_data.dataset.inter_feat)} 交互")
    print(f"  验证集: {len(valid_data.dataset.inter_feat)} 交互")
    print(f"  测试集: {len(test_data.dataset.inter_feat)} 交互")

    print("初始化模型...")
    model_class = get_model(config["model"])
    model = model_class(config, train_data.dataset).to(config["device"])

    print("开始训练...")
    trainer_class = get_trainer(ModelType.GENERAL, config["model"])
    trainer = trainer_class(config, model)
    best_model = trainer.fit(
        train_data,
        valid_data,
        saved=True,
        show_progress=config["show_progress"],
    )

    print("评估...")
    test_result = trainer.evaluate(test_data, load_best_model=True, show_progress=False)

    print("\n===== 测试结果 =====")
    print(f"Recall@10:  {test_result['recall@10']:.6f}")
    print(f"Recall@20:  {test_result['recall@20']:.6f}")
    print(f"NDCG@10:    {test_result['ndcg@10']:.6f}")
    print(f"NDCG@20:    {test_result['ndcg@20']:.6f}")

    # 保存结果
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "recall@10": float(test_result["recall@10"]),
        "recall@20": float(test_result["recall@20"]),
        "ndcg@10": float(test_result["ndcg@10"]),
        "ndcg@20": float(test_result["ndcg@20"]),
        "device": device_name,
        "epochs": epochs,
    }
    with open(output_dir / "recbole_metrics.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n结果已保存到 {output_dir / 'recbole_metrics.json'}")

    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="LightGCN smoke 训练（S1-b）")
    ap.add_argument("--data-path", type=Path, default=REPO_ROOT / "data" / "recbole",
                    help="RecBole 数据目录（默认: data/recbole）")
    ap.add_argument("--output", type=Path, default=REPO_ROOT / "results" / "_smoke" / "recbole",
                    help="输出目录（默认: results/_smoke/recbole）")
    ap.add_argument("--epochs", type=int, default=50, help="训练轮数（默认: 50）")
    ap.add_argument("--no-gpu", action="store_true", help="禁用 GPU（仅 CPU）")
    args = ap.parse_args()

    run_smoke(
        data_path=args.data_path,
        output_dir=args.output,
        epochs=args.epochs,
        use_gpu=not args.no_gpu,
    )
