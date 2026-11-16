# O-b 实验冻结

- 周次：W8 冻结实验，算法章成稿（01/04 周一 – 01/10 周日）
- 线：事务
- 估时：0.5 小时

## 提示词

打 git tag exp-freeze。在 CLAUDE.md 红线中追加一条：“exp-freeze 之后不新增实验与功能；补跑与修 bug 需在 docs/decisions.md 写明原因与影响的表格。”
运行一次 make backup，并列出 results/ 中所有被 configs/tables.yaml 引用的结果目录，确认都已备份。

## 产出
tag exp-freeze；更新后的 CLAUDE.md

## 验收
备份清单与表格引用一一对应

## 论文落点
无
