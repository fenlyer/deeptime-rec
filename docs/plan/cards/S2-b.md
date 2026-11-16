# S2-b 冻结测试目标口径

- 周次：W2 基线（11/23 周一 – 11/29 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S2-a 中 LightGCN 完成

## 提示词

用 LightGCN 5 个 seed 的 per_user.parquet，分别按“全部测试目标”和“仅 rating≥4 目标”计算 Recall@10/20、NDCG@10/20 和用户数，生成 results/target_policy/compare.json 与一张对比表。
不要替我做决定，把两种口径的用户数、指标和差异列出来。
我决定后：把决定写进 docs/预处理口径冻结.md 第一节与 docs/decisions.md，在 configs/eval.yaml 固定默认口径，并说明另一种口径的结果放附录。

## 产出
results/target_policy/compare.json；更新后的口径冻结文件与 configs/eval.yaml

## 验收
口径写入三处且一致

## 论文落点
第 3 章实验设置：测试目标口径；附录：另一口径的结果
