# S4b-b 排序主实验、消融、敏感性

- 周次：W6 排序、端到端与 v2（12/21 周一 – 12/27 周日）
- 线：研究线
- 估时：1 天人工 + 约 1 GPU 天
- 依赖：S4b-a

## 提示词

isolated 协议，5 个 seed：Temporal-DIN；+User Memory（特征增强，不蒸馏）；+蒸馏（完整）。
消融（5 seed）：去时间偏置、去 Memory、去门控（改为拼接）、去蒸馏。表中“去 Memory 与蒸馏”一行如仍保留时间偏置，标签写成“Temporal-DIN（无 Memory、无蒸馏）”，不要叫“标准 DIN”。
敏感性（3 seed）：η ∈ {0, 0.1, 0.3, 0.5, 1.0}、τ ∈ {1, 2, 4}、N ∈ {5, 10, 20}、g ∈ {linear, log}、κ ∈ {0, 1}。
结果放 results/rank_main/、rank_ablation/、rank_sens/；完整模型 vs DIN、完整 vs 无蒸馏的按用户配对检验写入 results/rank_main/gate_G6.json。

## 产出
results/rank_main/；rank_ablation/；rank_sens/；gate_G6.json

## 验收
主表与消融 5 seed 齐全；gate_G6.json 生成

## 论文落点
第 4 章主结果、消融、敏感性（替换 V8 表 5-6、5-12、5-14）
