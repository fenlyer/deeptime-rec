# S-rank-distill LLM 蒸馏（升级版）

- 周次：W4（12/11 – 12/17）
- 线：研究线
- 估时：2 天
- 依赖：S-rank-main

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ⚠️ 可选（LLM API 调用可用 CPU，联合训练需 GPU） |
| **SSH** | 可选 |
| **API Key** | 需要 Qwen API Key（或 DashScope logprobs 接口） |
| **时长** | ~10h（含 API 调用 + 联合训练） |

## 目标

最小可行蒸馏：是/否概率软标签 + 联合训练 + 教师质量评估。

## 升级要点（相对简化版）

1. **教师信号改为是/否概率软标签**：读模型 logprobs，计算
   `r_T = exp(ℓ_yes) / (exp(ℓ_yes) + exp(ℓ_no))`
2. **保留联合训练**：`L = α × L_task + β × L_distill`，α=0.7，β=0.3
3. **新增表 4-6 教师质量评估**：验证集上计算教师 AUC / Brier 分数 / 校准曲线
4. **砍掉**：τ（温度）与 β 的敏感性扫描

## 实现流程

```python
# 1. User Memory 生成（Qwen API，~2h）
# 2. 教师信号生成（是/否 logprobs，~4h）
#    r_T = exp(ℓ_yes) / (exp(ℓ_yes) + exp(ℓ_no))
# 3. 联合训练（α=0.7, β=0.3，~3h）
# 4. 教师质量评估（AUC/Brier/校准曲线）
```

## 前置确认

- [ ] 所选模型服务能否返回词元级 logprobs
  - 若 Qwen-7B-Chat API 不支持 → 改用 DashScope logprobs 接口
  - 若仍不可用 → 本地部署 Qwen-7B（AutoDL 24GB 可跑）
  - 最终降级 → 退回 V8"直接生成浮点分数"方案

## 产出

- `artifacts/user_memory.npy`
- `artifacts/teacher_signals/` 教师信号
- `results/ch4_rank/temporal_din_distill/seed{n}/`

## 降级说明

- 蒸馏敏感性（表 4-7）：α/β 仅留"本文设定值"一行，不扫
- γ/N 敏感性：并入 S-rank-main

## 验收

- [ ] User Memory 生成完成
- [ ] 教师信号（是/否 logprobs）生成完成
- [ ] 联合训练完成
- [ ] 表 4-6 教师质量评估完成（AUC/Brier/校准曲线）
- [ ] 数字填入表 4-2（Temporal-DIN+蒸馏完整版行）
- [ ] 数字填入表 4-5（消融：移除蒸馏 / 移除蒸馏+User Memory）

## 论文落点

- **表 4-2**：排序主结果 → Temporal-DIN+蒸馏（完整版）行 ← 主结果
- **表 4-5**：消融 → 移除蒸馏 / 移除蒸馏+User Memory（2 行）
- **表 4-6**：教师质量（AUC/Brier/校准曲线）← 从 deferred 拉入
- **4.4.2 节**：教师信号生成（是/否概率，须 logprobs 支持）
- **附录 A**：Prompt 原文（User Memory + 教师信号）
