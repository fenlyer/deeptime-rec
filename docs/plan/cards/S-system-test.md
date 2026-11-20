# S-system-test 系统评测

- 周次：W4（12/15 – 12/18）
- 线：研究线
- 估时：1 天
- 依赖：S-rank-distill、工程线 E-serve

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ❌ 不需要（CPU 推理） |
| **SSH** | 可选（可本机测试） |
| **时长** | ≈ 1 小时 |

## 目标

简单系统评测：延迟 + 一致性校验。

## 简化策略

1. **不做压测**：单并发测延迟即可
2. **一致性校验**：只抽样 10 个用户
3. **解释评估**：推迟（非毕业必需）

## 评测项

### 1. 延迟测试（表 5-9、5-10）

```python
# 单并发，100 次请求取平均
latency = {
    "cache_lookup": 2,    # ms
    "feature_load": 3,
    "recall": 10,
    "rank": 25,
    "rerank": 3,
    "total": 43
}
```

### 2. 一致性校验（表 5-11）

```python
# 抽样 10 个用户，比较离线 vs 在线结果
consistency = {
    "n_users": 10,
    "recall_match": 1.0,  # 完全一致
    "rank_match": 0.9
}
```

## 产出

- `results/ch5_system/latency.json`
- `results/ch5_system/consistency.json`

## 验收

- [ ] 延迟测试完成
- [ ] 一致性校验完成
- [ ] 数字填入表 5-9、5-10、5-11

## 论文落点

V9 表 5-9、5-10、5-11
