# S4a-a vLLM 部署与测速，定预算

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：研究线
- 估时：0.5 天

## 提示词

在单独的 conda 环境 llm 中部署 vLLM，模型 Qwen2.5-7B-Instruct（bf16）。把 HuggingFace 仓库 revision hash、vLLM 版本、max_model_len、gpu_memory_utilization 写入 llm/README.md 与 docs/decisions.md。
写 llm/bench.py：用 1000 条真实格式的 Prompt（取训练集历史构造）分别测 Memory 生成的输出 token/s，以及“是/否”打分的条/秒（开启前缀缓存）。
据此估算全量耗时，写 results/llm/budget.json，并给出两档方案：全量用户 / 抽样 N 万用户做蒸馏（Memory 始终全量）。由我决定。

## 产出
llm/README.md；llm/bench.py；results/llm/budget.json

## 验收
两档方案的耗时估算齐全，决定已写入 decisions.md

## 论文落点
第 4 章实验设置：教师模型、版本、温度、时长
