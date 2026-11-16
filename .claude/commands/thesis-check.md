---
description: 论文一致性检查（只报告，不改正文）
---
运行 scripts/check_thesis.py 与 scripts/check_refs.py，再补充脚本难以发现的问题：
- 未解析的占位符；正文中不经占位符出现的实验数字；
- 禁用词与评价性套话（列出位置）；
- 与 thesis/src/symbols.md 冲突的符号；公式、图、表编号是否连续；
- 引用 key 不在 bib、bib 中有未引用条目、条目缺 DOI/URL；
- 同一事实前后不一致（向量维度、矩阵规模、MLP 结构、并发数、延迟、内存）；
- 论文描述与代码不一致（以代码和配置为准，附文件:行号）。
输出 docs/weekly/thesis_check_<日期>.md，按章节排序。不修改 thesis/src/。
