# S1-b RecBole 冒烟测试与冻结切分对接

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：1 天
- 依赖：S0-a、S1-a

## 提示词

目标：确认 RecBole 与 RecBole-GNN 能在本机运行，并且读取我们冻结好的切分，而不是让它自己切。
1. 在独立 conda 环境中安装 RecBole 与 RecBole-GNN，用自带小数据集跑 LightGCN 1 个 epoch。若与 Python 3.12 / PyTorch 2.4 不兼容，新建 Python 3.10 环境；把选择和全部版本号写入 environment/recbole.yml 与 docs/decisions.md。
2. 写 data/to_recbole.py：把 processed/IS 的 train/val/test 转成 RecBole atomic 文件，用 benchmark_filename 方式加载，字段含 user_id、item_id、rating、timestamp。
3. LightGCN 在 IS 上训练（seed 0，可先少轮数），同一个 checkpoint 分别用 RecBole 自带评估和 eval/full_rank.py 评估。
4. 写 eval/crosscheck_recbole.py，比较两边 Recall@10/20、NDCG@10/20 的差值和逐用户 rank 一致的比例。
不一致时先查屏蔽规则（测试时是否屏蔽训练+验证物品）与 ID 映射，不要改 eval/ 去迁就 RecBole。

## 产出
environment/recbole.yml；data/to_recbole.py；eval/crosscheck_recbole.py；results/_smoke/crosscheck.json

## 验收
四个指标差值 < 1e-4，且 ≥ 99.9% 用户 rank 一致；不一致的用户逐个说明原因

## 论文落点
第 3 章实验设置：基线实现来源（RecBole，CIKM 2021）
