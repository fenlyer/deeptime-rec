# S3-b 主实验、消融、变体 × 5 seed

- 周次：W3 TI-LightGCN 主实验（11/30 周一 – 12/06 周日）
- 线：研究线
- 估时：1 天人工 + 约 1 GPU 天
- 依赖：S3-a

## 提示词

用 configs/recall/ti_lightgcn_IS.yaml，在 seed 0 上做小网格调参（λ ∈ {0.5, 1, 2}×λ0、μ ∈ {1e-3, 1e-2}、α 比值两组），只看验证集，选定后记入 docs/decisions.md。
然后以下配置各跑 5 个 seed，结果放 results/recall_ti/{config}/：
完整；去反馈权重；去时间衰减；两者都去；去长尾正则；负反馈 drop；用户相对时钟。
全部完成后：
- 用 eval/paired_test.py 计算每个配置 vs LightGCN，以及完整 TI vs SimGCL；
- 生成 results/recall_ti/gate_G3.json：完整 TI 相对 LightGCN 在 R@10、N@10 上的均值差、p、d_z，以及是否 p < 0.05。
只汇报事实，不对结果做解释性包装。

## 产出
results/recall_ti/；results/recall_ti/gate_G3.json

## 验收
7 配置 × 5 seed 齐全；gate_G3.json 生成

## 论文落点
第 3 章主结果表、消融表、变体对比表
