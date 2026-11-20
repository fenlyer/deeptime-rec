# S-rank-distill LLM 蒸馏（简化版）

- 周次：W4（12/11 – 12/15）
- 线：研究线
- 估时：1 天
- 依赖：S-rank-main

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ⚠️ 可选（LLM API 调用可用 CPU） |
| **SSH** | 不需要（调用 Qwen API） |
| **API Key** | 需要 Qwen API Key |
| **时长** | ≈ 2 小时（API 调用） |

## 目标

简化版蒸馏：生成 User Memory，直接作为特征输入。

## 简化策略

1. **不做教师信号**：V9 要求生成"是/否概率"，简化为直接用 LLM 生成用户偏好摘要
2. **不做联合训练**：User Memory 作为静态特征，不参与梯度
3. **蒸馏权重 η**：固定 0.5（不做敏感性）

## 实现

```python
# 简化流程
1. 调用 Qwen API，为每个用户生成 256 维偏好摘要
2. 存入 `artifacts/user_memory.npy`
3. Temporal-DIN 读取作为长期通道输入
```

## 产出

- `artifacts/user_memory.npy`
- `results/ch4_rank/temporal_din_distill/seed{n}/`

## 简化说明

- 教师质量评估（表 4-6）推迟
- 蒸馏敏感性（表 4-7）推迟

## 验收

- [ ] User Memory 生成完成
- [ ] 蒸馏版实验完成
- [ ] 数字填入表 4-5（消融的一行）

## 论文落点

V9 表 4-5（排序模块消融）+蒸馏行
