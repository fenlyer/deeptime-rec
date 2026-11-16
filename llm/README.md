# llm/ — 教师模型与 User Memory

- **用途**：LLM 教师部署、User Memory 生成、蒸馏打分。
- **输入**：用户训练历史、商品元数据、vLLM 服务。
- **产出**：`user_memory.jsonl`、`teacher_scores.parquet`、教师质量评估。
