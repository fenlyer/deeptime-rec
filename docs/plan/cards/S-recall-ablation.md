# S-recall-ablation 消融实验

- 周次：W2（11/27 – 12/03）
- 线：研究线
- 估时：1 天
- 依赖：S-recall-main

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ✅ 需要 |
| **SSH** | 需要登录 AutoDL 服务器 |
| **时长** | 3 变体 × 3 seed ≈ 6 小时 |

## 目标

跑 3 个消融变体，验证各组件贡献。

## 变体设计

| 变体 | 移除组件 | 做法 |
|-----|---------|------|
| w/o 时间衰减 | λ=0 | 修改 config 中 λ=0 |
| w/o 反馈强度 | α_r=1（全部等权） | 修改 config 中 α_r 全为 1 |
| w/o 长尾正则 | γ=0 | 修改 config 中 γ=0 |

## 产出

- `results/ch3_recall/ablation/{variant}/seed{n}/` 9 个结果目录（3 变体 × 3 seed）

## 简化说明

- 只做 3 seed（不 5 seed），节省时间
- 不做设计变体对比（表 3-9 推迟到后续整改）

## 论文落点：表 3-8 对齐

V9 表 3-8 共 5 行（4 变体 + 1 基准）：

| 表 3-8 行 | 数据来源 |
|----------|----------|
| 完整 TI-LightGCN（基准） | S-recall-main 结果 |
| w/o 反馈强度权重 | 本卡片变体 2 |
| w/o 时间衰减 | 本卡片变体 1 |
| w/o 两者（= LightGCN） | **复用 S-recall-base 的 LightGCN 结果**，不重跑 |
| w/o 长尾正则化项 | 本卡片变体 3 |

> "w/o 两者" 即 λ=0 且 α_r=1，等价于标准 LightGCN。直接取 `results/ch3_recall/baselines/lightgcn/seed{0-2}/` 的前 3 seed 结果。

## 验收

- [ ] 9 个 run 完成
- [ ] LightGCN 复用数据校验（seed 0-2 与 baselines 一致）
- [ ] 数字填入论文表 3-8（5 行 × 3 列）
