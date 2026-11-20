# S-rank-main Temporal-DIN 实现与主实验

- 周次：W3-W4（12/08 – 12/15）
- 线：研究线
- 估时：3 天
- 依赖：S-rank-base

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ✅ 需要 |
| **SSH** | 需要登录 AutoDL 服务器 |
| **时长** | 1 模型 × 5 seed ≈ 8 小时 |

## 目标

实现 Temporal-DIN 并跑主实验。

## 模型设计

### 核心改动（相对 DIN）

1. **时间偏置注意力**：`a_k = softmax(a(h, e_i) - γ × Δt_k / T)`
   - γ = 0.3（默认），可调
2. **双通道**：
   - 短期通道：最近 N 条行为（N=5）
   - 长期通道：User Memory 向量（256 维）
3. **门控融合**：`h = g ⊙ h_short + (1-g) ⊙ h_long`

### 实现文件

- `rank/models/temporal_din.py`：模型定义
- `rank/layers.py`：时间注意力层、门控层

## 产出

- `results/ch4_rank/temporal_din/seed{n}/` 5 个结果目录
- 数字填入表 4-2 最后一行

## 简化说明

- 不做蒸馏（简化版）
- User Memory 直接拼接，不做门控（可后续改进）

## 验收

- [ ] 代码实现完成
- [ ] 5 seed 实验完成
- [ ] 数字填入表 4-2

## 论文落点

V9 表 4-2 Temporal-DIN 行
