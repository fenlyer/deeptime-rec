# S4a-b User Memory 生成与防泄漏

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：研究线
- 估时：1 天 + 夜间批跑
- 依赖：S4a-a

## 提示词

写 llm/build_memory.py：
- 输入只用每个用户的训练集交互（商品标题、类目、评分、时间），按时间排序取最近 M 条（M 写进配置）。Prompt 模板放 llm/prompts/memory_v1.txt，要求输出固定 JSON 字段（关注品类、常见用途、品牌倾向、偏好变化），禁止写入历史中没有的信息。
- 温度 0，批量推理，断点续跑（已完成的 user_id 跳过），输出 artifacts_llm/user_memory.jsonl，每行带 data tag、模型 revision、prompt 版本。
- 用 paraphrase-multilingual-MiniLM-L12-v2 编码为 384 维 memory_emb.npy。
- llm/check_leak.py：断言任何用户的 Prompt 中都不含其验证或测试物品的 ID 与标题；随机抽 50 条生成 results/llm/memory_review.csv（Prompt、输出、空白的人工判断列）供我检查。
全量任务放进 queue.txt 夜间执行，前台不要等待。

## 产出
llm/build_memory.py；llm/prompts/memory_v1.txt；user_memory.jsonl；memory_emb.npy；results/llm/memory_review.csv

## 验收
check_leak 0 命中；覆盖用户数等于计划数；50 条人工检查完成

## 论文落点
第 4 章 User Memory 小节；附录 Prompt；V8 中“256 维”“注册行业”等说法据此改正
