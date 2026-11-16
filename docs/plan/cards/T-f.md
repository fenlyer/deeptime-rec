# T-f 第 5 章设计部分

- 周次：W7 解释评估与系统测试（12/28 周一 – 01/03 周日（含元旦，按 4 个工作日排））
- 线：写作线
- 估时：1 天（你写，对照表可由 Claude Code 起草）
- 依赖：E0-a、E3

## 提示词

1. 根据 docs/prototype_inventory.md、serving/、artifacts/v2/manifest.json，起草 thesis/src/05_system.md 中的“目标架构 / 原型实现”对照表：职责 | 目标架构 | 原型实现。原型实现一列只能写代码里真实存在的东西。对照表属于事实罗列，可以直接写入。
2. 用 Mermaid 画架构图、在线推荐时序图、数据实体关系图草稿，放 thesis/figures_src/，我再调整。
3. 列出 V8 第 3、6 章中应删去或移入“目标架构”列的描述（MySQL binlog、Redis RDB/AOF、IVF-PQ、2 核 2GB、APScheduler 每日重训等），逐条给出位置。

## 产出
05_system.md 对照表；thesis/figures_src/*.mmd；删改清单

## 验收
对照表“原型实现”列每一项都能在代码里找到

## 论文落点
第 5 章 5.1–5.4
