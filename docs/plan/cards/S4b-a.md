# S4b-a Temporal-DIN 与统一蒸馏损失

- 周次：W6 排序、端到端与 v2（12/21 周一 – 12/27 周日）
- 线：研究线
- 估时：1 天
- 依赖：S4a-c、S4b-0

## 提示词

在 rank/models/temporal_din.py 实现：
- 注意力：ã_k = softmax_k( a(e_k, e_c) − γ · g(Δt_k) )，g 支持 linear（Δt/Δ_day）与 log（ln(1 + Δt/Δ_day)）；γ 初值取 results/profile/IS.json 的 γ0，可选 learnable（softplus 参数化）。
- 短期通道：最近 N 条行为（N 可配）；长期通道：memory_emb（384 维，经线性层投影）；门控融合；MLP 结构从配置读取，论文按配置写。
- 损失：(1 − η)·BCE(y, σ(ℓ_S)) + η·τ²·ω·BCE(σ(ℓ_T/τ), σ(ℓ_S/τ))，ω = |2p_T − 1|^κ，κ = 0 时不加权。
测试 tests/test_temporal_din.py：
 (1) 两步写法（softmax 后乘衰减再归一化）与合成写法数值相等；
 (2) 所有 Δt 同加一个常数，注意力权重不变；
 (3) γ = 0 且去掉长期通道时，加载同一组权重后与 rank/models/din.py 的输出逐元素相等。

## 产出
rank/models/temporal_din.py；rank/losses.py；tests/test_temporal_din.py

## 验收
三项测试通过

## 论文落点
第 4 章模型与蒸馏目标（替换 V8 式 4-8、4-9、4-14 至 4-16）
