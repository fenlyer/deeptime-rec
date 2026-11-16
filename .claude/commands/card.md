---
description: 按执行计划开始一张任务卡
argument-hint: <卡片 ID，如 S1-a>
---
读 CLAUDE.md、docs/STATUS.md 和 docs/plan/cards/$ARGUMENTS.md。
1. 复述这张卡的目标、产出和验收标准，列出你需要读的文件。
2. 给出实现计划（文件、函数、测试），等我确认。
3. 确认后先写测试再实现；每完成一步运行一次相关测试。
4. 最后运行卡片中的验收命令，原样贴出输出；更新 docs/STATUS.md；给出以卡片 ID 开头的 commit message。
不做卡片范围以外的改动。遇到需要决定口径、数据或评估规则的问题，停下来问我。
