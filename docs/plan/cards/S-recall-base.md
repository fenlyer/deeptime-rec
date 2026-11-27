# S-recall-base 召回基线实验

- 周次：W1（11/20 – 11/26）
- 线：研究线
- 估时：2 天
- 依赖：S1-a（eval/）、S1-b（RecBole 对接）

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ✅ 需要（RecBole 训练） |
| **SSH** | 需要登录 AutoDL 服务器 |
| **环境** | conda activate rec（RecBole 环境） |
| **时长** | 5 模型 × 5 seed ≈ 20 小时（RTX 4090） |

## 目标

用 RecBole 跑 5 个召回基线模型，每个 5 个 seed，产出 25 个 run 的结果。

## 基线列表

| 模型 | RecBole 内置 | 备注 |
|-----|-------------|------|
| BPR-MF | ✅ | 矩阵分解基线 |
| NGCF | ✅ | 图协同过滤 |
| LightGCN | ✅ | 主流基线 |
| SGL | ✅ | 对比学习 |
| SimGCL | ✅ | 简化对比 |

## 产出

- `configs/recall/bprmf.yaml` 等 5 个配置文件
- `results/ch3_recall/baselines/{model}/seed{n}/` 25 个结果目录
- 每个目录含 `metrics.json`、`per_user.parquet`

## 实验配置

```yaml
# 统一配置
embedding_size: 64
train_batch_size: 2048
eval_args:
  split: {RS: [8,1,1]}  # 用冻结切分，不用默认
  group_by: user
  order: TO
  mode: full
metrics: [Recall, NDCG]
topk: [10, 20]
epochs: 200
stopping_step: 20
seed: [0,1,2,3,4]
```

## 验收

- [ ] 25 个 run 全部完成
- [ ] `results/ch3_recall/baselines/summary.csv` 生成
- [ ] 数字填入论文表 3-6

## 进度（2026-11-27）

代码部分已完成并提交（202f453），**正式 25 run 未跑**，阻塞于 AutoDL GPU。

| 项 | 状态 | 位置 |
|---|---|---|
| runner | ✅ | `experiments/run_recall_baseline.py` |
| 5 个配置 | ✅ | `configs/recall/*.yaml` |
| summary 脚本 | ✅ | `experiments/make_baseline_summary.py` |
| 单元测试（29 个） | ✅ | `tests/test_recall_baseline_runner.py` |
| CPU 冒烟（BPR/seed0/2epoch） | ✅ | `results/_smoke/recall/` |
| 队列（25 run + summary） | ✅ 已挂 | `experiments/queue.txt` |
| AutoDL 操作步骤 | ✅ | `autodl/S-recall-base.md` |
| **25 个正式 run** | ❌ 待 GPU | `bash experiments/queue.sh` |

下一步：在 AutoDL `rec` 环境（需先装 RecBole-GNN）执行队列，约 20 小时；
完成后回填 `git add results/ch3_recall/baselines && git push`。

## 论文落点

- **表 3-6**：3.5.2 召回主结果 → 前 5 行基线
- **表 3-15**：3.5.8 训练效率 → LightGCN/SGL/SimGCL 行
- **图 3-8/3-9**：数据提供（绘制归 T-ch3）
- 目录：`results/ch3_recall/baselines/{model}/seed{0-4}/`
