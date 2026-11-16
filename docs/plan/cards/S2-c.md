# S2-c 排序样本与排序评估框架

- 周次：W2 基线（11/23 周一 – 11/29 周日）
- 线：研究线
- 估时：1.5 天
- 依赖：S1-a

## 提示词

在 rank/ 下搭排序实验框架（不依赖 RecBole）：
- rank/samples.py：对训练集中每个用户的第 k 条交互（k ≥ 2）构造样本：历史 = 前 k−1 条（带时间戳），正样本 = 第 k 条；负样本 = 召回候选中的难负例 h 个 + 全库随机 r 个，h、r 写进 configs/rank/samples.yaml。候选文件路径作为参数；现在先用 LightGCN seed 0 导出的 Top-100 代替，W4 换成 TI-LightGCN。
- rank/eval_rank.py：给定每个测试用户的固定候选列表与打分，计算 AUC、GAUC、NDCG@10；--protocol isolated 时测试物品不在候选中则补入（日志记录补入比例），--protocol e2e 时不补入。
- rank/models/din.py：标准 DIN 作为第一个模型，seed 0 跑通。
- 测试：断言任何验证或测试物品都不出现在训练样本的正负样本与历史中；DIN smoke 的 AUC > 0.5 且训练损失下降。

## 产出
rank/samples.py；rank/eval_rank.py；rank/models/din.py；configs/rank/samples.yaml

## 验收
防泄漏测试通过；DIN smoke 结果写入 results/_smoke/din/

## 论文落点
第 4 章实验设置：样本构造、两套评估协议
