# S-recall-base v1 结果归档（2026-11-27）

重跑前的完整快照。用途：证明「补测训练过程数据」的重跑**不改变任何准确率数字**。

## 为什么归档

25 个正式 run 已跑完，但 `train_log.csv` 只有 `epoch,loss` 两列、`manifest.epoch_seconds` 是空数组，
缺少论文表 3-15（单Epoch耗时/峰值显存/图构建耗时）与图 3-9（per-epoch 验证 Recall）所需数据。
训练过程数据无法事后补，只能重跑。重跑前必须留一份对照基线。

## 目录

```
results/ch3_recall/_archive/v1-20261127/
├── {model}/seed{n}/    # 与 baselines/ 完全相同（126 个文件，16 MB）
└── summary.csv         # 逐 seed 的 4 个指标 + elapsed_s + best_epoch + git_commit
```

`_archive` 前缀以 `_` 开头，`scripts/make_tables.py` 的 `_model_dirs()` 会跳过，
不会把归档数字重复采集进 `numbers.json`。

## 产生的 commit

结果分两批跑出，非单一 commit：

| commit | run 数 |
|---|---|
| `10505ba` | 16 |
| `61e5bd6` | 9 |

## 实测基线（25 run，RTX 2080 Ti）

| 模型 | 5 seed 累计耗时 | 单 run 均值 | best_epoch 均值 |
|---|---|---|---|
| BPR-MF | 383 s | 77 s | 0.2 |
| LightGCN | 1058 s | 212 s | 12.2 |
| NGCF | 3418 s | 684 s | 57.0 |
| SGL | 7125 s | 1425 s | 82.4 |
| SimGCL | 1526 s | 305 s | 0.4 |
| **合计** | **13510 s ≈ 3.8 h** | — | — |

注：执行计划书写「RTX 4090 / ~20h」，实测为 RTX 2080 Ti / 3.8h。

## 重跑后怎么用

```bash
# 重跑完成后，与快照逐 seed 比对（验收 A1）
python experiments/snapshot_baselines.py \
    --runs-dir results/ch3_recall/baselines \
    --output /tmp/v2.csv
python experiments/snapshot_baselines.py --compare \
    results/ch3_recall/_archive/v1-20261127/summary.csv /tmp/v2.csv
```

退出码 0 = 4 个指标 × 25 个 run 全部一致（相对误差 < 1e-9）。
非 0 = 重跑改变了数字，须先排查（`PYTHONHASHSEED`、数据集加载顺序）再继续。

## 已知的 loss 列问题

`train_log.csv` 的 `loss` 列不可用于绘制训练曲线：

- BPR-MF 与 LightGCN 恒为 `105.358372`
- 其值精确等于 `批次总数(152) × ln2 = 105.3583714...`
- 原因：`RecBole Trainer._train_epoch` 对 `total_loss` 累加的是**每批的 mean loss**（约 `ln2`），
  而非张量求和；`train_loss_dict` 存的是这个累加值，所以与批大小无关

重跑时改为自行累积批量求和再除以样本数（决策 1 方案 b）。