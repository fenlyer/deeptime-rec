---
description: 运行第 N 周关口检查
argument-hint: <周次数字，如 3>
---
检查第 $ARGUMENTS 周关口是否通过。
1. 若 gates/w$ARGUMENTS.py 不存在：按 docs/plan/gates.md 中 G$ARGUMENTS 的条件实现它。每个条件一个函数，输出 PASS/FAIL、实际值和证据文件路径；人工确认项输出 MANUAL。检查必须读取真实产物，不允许为通过而放宽阈值。
2. 运行 python -m gates.w$ARGUMENTS，原样贴出输出。
3. 对每个 FAIL，给出最可能的 2–3 个原因和验证办法，不要动手修。
4. 把结果写入 docs/weekly/G$ARGUMENTS.md，并更新 docs/STATUS.md。
