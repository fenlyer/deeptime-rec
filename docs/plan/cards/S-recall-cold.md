# S-recall-cold 冷启动分层

- 周次：W3（12/04 – 12/08）
- 线：研究线
- 估时：0.5 天
- 依赖：S-recall-main

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ❌ 不需要（只做评估） |
| **SSH** | 不需要（本机运行） |
| **时长** | ≈ 10 分钟 |

## 目标

按训练集交互数分 4 层，报告分层指标。

## 分层定义（V9 表 3-11）

| 层次 | 训练集交互数 | 占比 | 代表场景 |
|-----|------------|------|---------|
| 超冷启动 | 0-4 | 53.7% | 新用户 |
| 冷启动 | 5-9 | 33.5% | 新用户 |
| 普通用户 | 10-29 | 11.9% | 活跃用户 |
| 重度用户 | ≥30 | 0.9% | 活跃用户 |

## 实现

复用 `eval/strata.py`（S1-c 已完成），只需传入结果目录。

## 产出

对以下模型做分层评估（全部为后处理，不重跑）：

| 模型 | 数据来源 | 对应论文表 |
|------|----------|-----------|
| LightGCN | `results/ch3_recall/baselines/lightgcn/` | 表 3-12 第 1 列 |
| SimGCL | `results/ch3_recall/baselines/simgcl/` | 表 3-12 第 2 列 |
| TI-LightGCN | `results/ch3_recall/ti_lightgcn/` | 表 3-12 第 3 列 |

输出文件：
- `results/ch3_recall/cold_start/lightgcn.json`
- `results/ch3_recall/cold_start/simgcl.json`
- `results/ch3_recall/cold_start/ti_lightgcn.json`

## 验收

- [ ] 3 个模型的分层结果生成
- [ ] 加权守恒检查通过：Σ(nᵢ·metricᵢ)/Σnᵢ = 全体用户值
- [ ] 数字填入表 3-12（3 模型 × 4 层 + 全体）

## 论文落点

- **表 3-11**：分层定义
- **表 3-12**：模型分层对比（LightGCN / SimGCL / TI-LightGCN × 4 层）
- **图 3-11**：分层增益柱状图（TI-LightGCN 相对 LightGCN 的各层相对提升）
- 守恒校验：Σ(nᵢ·metricᵢ)/Σnᵢ = 全体用户值

## 推迟项

- **表 3-13**（"完整系统" 分层）：需要多路召回 + User Memory，推迟到 S-system-test 卡片
- **图 3-11** 中 "完整多路召回" 柱：同上，届时补充
