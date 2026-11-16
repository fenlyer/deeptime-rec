# S6-a 解释质量：自动、LLM 评审、人工

- 周次：W7 解释评估与系统测试（12/28 周一 – 01/03 周日（含元旦，按 4 个工作日排））
- 线：研究线
- 估时：1 天 + 标注者 2 小时
- 依赖：E4、O-a

## 提示词

1. 从测试集按固定 seed 抽 100 个（用户，推荐商品）对，推荐商品取 v2 系统 Top-10 中的一个；生成三种解释：无 RAG、RAG、模板。
2. eval/explain_attr.py：从解释中抽取品牌、材质、尺寸、数值参数，与 item_meta 的 details 比对，计算属性一致率；涉及价格的句子单独统计（IS 价格字段覆盖率只有 74.7%）。
3. eval/llm_judge.py：用与生成模型不同的模型，按 docs/rubric.md 打分，记录模型名与版本。
4. 生成 annotate/index.html：单文件离线标注页，三种解释随机顺序、隐藏来源，结果导出 CSV。我发给 3 名标注者。
5. 收回 CSV 后计算各维度均值、Fleiss κ、LLM 评审与人工评分的 Spearman 相关，输出 results/explain/。BLEU/ROUGE 只作辅助列。

## 产出
eval/explain_attr.py；eval/llm_judge.py；annotate/index.html；results/explain/

## 验收
属性一致率、LLM 评审、人工均值与 κ 都已输出

## 论文落点
第 5 章解释质量评估（替换 V8 5.9 的“5 位专家”与表 5-15、5-16）
