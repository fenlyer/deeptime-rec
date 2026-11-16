# W0-a 仓库骨架、CLAUDE.md 与自定义命令

- 周次：W0 启动日（11/15 周日（最迟 11/16 上午完成））
- 线：事务
- 估时：2 小时
- 依赖：本页顶部的“下载 bootstrap.md”

## 说明
开始前：把本页 HTML、两份路线图 HTML、整改V8_1112.docx 放进仓库 docs/revision/，把 bootstrap.md 放进 docs/plan/，然后在仓库根目录启动 Claude Code。

## 提示词

先读 docs/plan/bootstrap.md（由执行计划页面导出，按“=== FILE: 路径 ===”分隔了多个文件）。
1. 按其中的路径写出各文件：CLAUDE.md、.claude/commands/*.md、docs/STATUS.md、docs/decisions.md、docs/plan/gates.md、docs/plan/cards/<卡片ID>.md。同名文件已存在时先给我看差异，不要直接覆盖。
2. 按 CLAUDE.md“目录”一节补齐缺失目录，每个目录放一个 README.md，写明用途、输入、产出（各 3 行以内）。
3. .gitignore 排除 data/processed/、artifacts/、build/、*.npy、*.pt、*.parquet、*.index。
4. data/ 下已有脚本只允许 git mv 调整位置，不改内容。
完成后列出新建和移动的文件清单，等我确认再提交（commit message：W0-a: 仓库骨架与规则）。

## 产出
CLAUDE.md；.claude/commands/ 下 6 个命令；docs/plan/cards/；docs/STATUS.md；docs/decisions.md

## 验收
在 Claude Code 里输入 / 能看到 card、gate、weekly 等命令；git status 干净

## 论文落点
无
