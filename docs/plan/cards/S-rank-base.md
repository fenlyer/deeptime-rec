# S-rank-base 排序基线实验

- 周次：W3（12/04 – 12/08）
- 线：研究线
- 估时：1 天
- 依赖：S-recall-main（需要召回嵌入）

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ✅ 需要 |
| **SSH** | 需要登录 AutoDL 服务器 |
| **时长** | 1 模型 × 5 seed ≈ 5 小时 |

## 目标

跑 DIN 基线（简化：只跑一个排序基线）。

## 实现

用 RecBole 的 DIN 实现：
- 候选集：TI-LightGCN 召回的 Top-100
- 特征：user_id, item_id, 行为序列（最近 N 条）

## 产出

- `configs/rank/din.yaml`
- `results/ch4_rank/baselines/din/seed{n}/` 5 个结果目录

## 简化说明

- DIEN 推迟（RecBole 无内置，需自研）
- 只报 AUC、NDCG@10

## 验收

- [ ] DIN 5 seed 完成
- [ ] 数字填入表 4-2 基线行

## 论文落点

- **表 4-2**：4.5.2 DIN 行
- **表 4-1**：基线汇总
- **图 4-3**：DIN 训练曲线
