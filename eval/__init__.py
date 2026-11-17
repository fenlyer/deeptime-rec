"""统一评估入口（S1-a）

在 eval/ 下实现：
- metrics.py  : 给定每个用户测试物品的排名，计算 Recall@K / NDCG@K
- full_rank.py: 输入打分函数 + 屏蔽集合，输出 per_user.parquet

先写测试（tests/test_eval.py），再写实现。
"""