# S1-a 统一评估入口 eval/

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：1 天

## 提示词

在 eval/ 下实现统一评估，先写测试再写实现：
- metrics.py：给定每个用户测试物品的排名，计算 Recall@K（LOO 下等于 HR@K）与 NDCG@K（IDCG=1），K ∈ {10, 20}。
- full_rank.py：输入用户与物品嵌入（或一个打分函数），对全部物品打分，屏蔽该用户的训练和验证物品，输出 per_user.parquet，列为 user_id, test_item, rank, test_item_in_train, test_rating。
- 并列分数取悲观排名（与测试物品同分的物品都算排在它前面），在 docstring 写清楚。
- 支持两种测试目标口径：--target all（全部测试目标）与 --target pos（只评 rating≥4 的目标），默认值从 configs/eval.yaml 读取。
tests/test_eval.py：3 个用户、6 个物品的手算样例，覆盖屏蔽、并列、K 边界、两种口径。
另写一个检查：同一份打分评估两次，per_user.parquet 的 sha256 必须相同。pytest 全过后给我看。

## 产出
eval/metrics.py；eval/full_rank.py；configs/eval.yaml；tests/test_eval.py

## 验收
pytest tests/test_eval.py 全过；重复评估 hash 一致

## 论文落点
评价指标公式改写为 LOO 化简形式（式 5-1 的替代），“全排序、屏蔽训练与验证物品”的说明
