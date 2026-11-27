# S-recall-main TI-LightGCN 主实验

- 周次：W1-W2（11/24 – 12/01）
- 线：研究线
- 估时：2 天
- 依赖：S-recall-base（对比需要基线结果）

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ✅ 需要（模型训练） |
| **SSH** | 需要登录 AutoDL 服务器 |
| **环境** | conda activate rec |
| **时长** | 1 模型 × 5 seed ≈ 4 小时 |

## 目标

实现 TI-LightGCN 并跑 5 seed 主实验。

## 实现要点

1. `models/ti_lightgcn.py`：继承 RecBole 的 LightGCN，修改边权计算
2. 边权函数：`w(u,i) = α_r × exp(-λ × Δt / T)`
   - α_r：评分反馈强度（表 3-1）
   - λ = 0.001（时间衰减率）
   - T = 86400（秒/天）
   - Δt = T_now - t（距最新时间戳的秒数）
3. 长尾正则：γ = 0.01，阈值 θ = 10

## 产出

- `models/ti_lightgcn.py`
- `configs/recall/ti_lightgcn.yaml`
- `results/ch3_recall/ti_lightgcn/seed{n}/` 5 个结果目录
- `tests/test_ti_lightgcn.py` 单元测试

## 验收

- [ ] 代码实现完成
- [ ] 5 seed 实验完成
- [ ] 数字填入论文表 3-6 最后一行

## 论文落点

- **表 3-6**：最后一行 TI-LightGCN + 相对提升行
- **表 3-1/3-2**：α_r 权重 / 复杂度对比
- **表 3-15**：TI-LightGCN 行（参数量 4.9M）
- 目录：`results/ch3_recall/ti_lightgcn/seed{0-4}/`（含 per_user.parquet）
