# S3-f 冻结召回模型，导出候选集

- 周次：W4 召回收尾与冻结（12/07 周一 – 12/13 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S3-b、S3-e

## 提示词

1. 把 TI-LightGCN 最终配置写进 docs/decisions.md，打 git tag recall-freeze。
2. 用 seed 0 的最终 checkpoint 为全体 IS 用户导出 Top-100 候选（屏蔽训练与验证物品），保存 results/candidates/ti_top100.parquet；另存一份屏蔽训练物品、用于构造排序训练难负例的版本。
3. 记录测试物品被 Top-100 覆盖的比例，写入 results/candidates/coverage.json。
4. 把 rank/ 的候选文件默认路径改为这个文件，重跑 DIN smoke 确认流程无误。

## 产出
results/candidates/；tag recall-freeze

## 验收
coverage.json 生成；DIN smoke 在新候选上正常

## 论文落点
第 4 章实验设置：候选集来源与覆盖率
