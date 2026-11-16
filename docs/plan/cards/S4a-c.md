# S4a-c 教师打分与教师质量

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：研究线
- 估时：1 天 + 夜间批跑
- 依赖：S4a-b、S3-f

## 提示词

写 llm/teacher_score.py：
- 对 rank/samples.py 产出的训练样本对 (u, i)，Prompt = 该用户 Memory + 训练历史摘要 + 候选商品标题与类目，要求只回答“是”或“否”；max_tokens=1，用 vLLM 的 logprobs 读取首个生成位置上这两个 token 的对数概率（必要时用 allowed_token_ids 限定为这两个 token），ℓ_T = log p(是) − log p(否)，它等于两者 logit 之差。打分时 temperature 设为 1.0，读到的是模型原始分布的对数概率，生成的那个 token 本身不用。存 teacher_scores.parquet（含 prompt 版本）。
- 先确认分词器中“是”“否”各为单个 token；不是的话换成单 token 的候选词，并写进 decisions.md。
- 质量评估：取验证集 5000 个用户 × 其 TI 候选中 20 个物品（含验证物品）打分，计算教师 AUC、GAUC、ECE，画可靠性图，输出 results/llm/teacher_quality.json 与 figures/llm/。
打分规模按 budget.json 的决定执行，放夜间队列。

## 产出
llm/teacher_score.py；teacher_scores.parquet；results/llm/teacher_quality.json；可靠性图

## 验收
teacher_quality.json 与图生成；打分覆盖的样本数等于计划数

## 论文落点
第 4 章蒸馏小节与教师质量分析（V8 中“输出 0–1 浮点分数”的做法据此替换）
