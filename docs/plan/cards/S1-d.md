# S1-d 表格与数字管线骨架

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S1-c

## 提示词

写 scripts/make_tables.py 与 scripts/build_thesis.py 的骨架（格式见执行计划附录 D）：
- make_tables.py 读取 results/ 下的 metrics.json（多 seed 汇总为均值±标准差），按 configs/tables.yaml 的定义生成 thesis/generated/tables/{name}.md，并把每个单元格登记进 thesis/generated/numbers.json：key → {value, display, sources, command, commit, data_tag}。显著性标记由 paired_test 的 JSON 决定，不手写。
- build_thesis.py 把 thesis/src/*.md 中的 {{n:key}} 与 {{table:name}} 替换为实际内容，输出 build/thesis.md；遇到不存在的 key 报错退出；--audit 模式在每个数字后追加〔来源文件〕。
- scripts/check_thesis.py：列出未解析的占位符、正文中不经占位符出现的小数或百分数、禁用词。
现在 results/ 里没有正式结果：用 tests/fixtures/ 下的假结果目录测试，fixtures 里的数字不能出现在 thesis/src/。

## 产出
scripts/make_tables.py；scripts/build_thesis.py；scripts/check_thesis.py；configs/tables.yaml

## 验收
对 fixtures 能生成表格与 numbers.json；缺 key 时报错退出

## 论文落点
之后所有表格与正文数字的唯一来源
