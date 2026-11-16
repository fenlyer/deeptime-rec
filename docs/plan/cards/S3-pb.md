# S3-pb Plan B：插件化到 SimGCL（仅当 G3 不显著）

- 周次：W3 TI-LightGCN 主实验（11/30 周一 – 12/06 周日）
- 线：研究线
- 估时：1.5 天（条件执行）
- 依赖：gate_G3.json

## 提示词

仅当 gate_G3.json 中完整 TI 相对 LightGCN 不显著时执行。
1. models/ti_simgcl.py：在 SimGCL 的传播上使用 build_weighted_adj() 的加权邻接（复用函数，不复制代码），5 个 seed，报告 TI-SimGCL vs SimGCL 的配对检验。
2. 按“用户内评分方差 = 0 / > 0”与“训练时间跨度三分位”分组，输出 TI vs LightGCN 在各组的差值与检验，写入 results/recall_ti/by_group.json。
3. 在 docs/decisions.md 记录：Plan B 已启动，第 3 章论点改为“与对比学习正交、可叠加，并给出适用边界”。

## 产出
models/ti_simgcl.py；results/recall_ti_simgcl/；results/recall_ti/by_group.json

## 验收
TI-SimGCL 5 seed 齐全；分组结果生成

## 论文落点
第 3 章论点调整（见“关口与 Plan B”）
