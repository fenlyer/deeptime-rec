---
description: 追溯论文中一个数字的来源
argument-hint: <数字或 numbers.json 的 key>
---
在 thesis/src/、thesis/generated/numbers.json、results/ 中查找 "$ARGUMENTS"：
给出它在论文中的全部位置、对应的 key、来源文件、生成命令、manifest 中的 git commit 与 data tag。
如果它是裸数字（不经占位符）或找不到来源，明确标为"无来源"，并列出可能对应的结果文件。
