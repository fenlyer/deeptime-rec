# T-l 构建 V9 与引用检查

- 周次：W9 V9 全文初稿（01/11 周一 – 01/17 周日）
- 线：写作线
- 估时：0.5 天
- 依赖：T-k

## 提示词

运行 make thesis 生成 build/thesis_V9.docx，然后运行 scripts/check_refs.py（没有就先写）：
- 正文引用的每个 key 都在 bib 中，且条目有 DOI 或 URL；
- bib 中没有未被引用的条目；
- citeproc 输出的编号按首次出现顺序单调递增；
- refs/verify.csv 中结论为“删除”的条目没有被引用。
再对全文运行 /thesis-check，汇总成一份清单交给我。

## 产出
build/thesis_V9.docx；引用检查报告

## 验收
引用检查 0 问题

## 论文落点
参考文献表
