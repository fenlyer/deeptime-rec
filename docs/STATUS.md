# STATUS
当前周：W1（11/16–11/22） 本周关口：G1（11/21）

## 进行中
- RecBole 结合方案已确认（见 decisions.md 2026-11-17），adapter 与对账校验待实现（S1-b）

## 已完成（卡片 ID｜commit｜日期）
- W0-a｜仓库骨架与规则（CLAUDE.md、6 个命令、58 张卡片、目录与 README、Makefile 骨架）｜2026-11-16
- W0-b｜三样外部信息已确认（送审截止 2027-06、CNKI TMLC2 ≤10%/15%、AIGC ≤10%、模板已放入 thesis/template/）｜2026-11-17
- W0-c｜数据盘确认（RTX 4090 / 数据盘 50G）；experiments/queue.sh 已完成；backup 简化为 git 追踪（删除 backup.sh 与 Makefile backup 目标）｜2026-11-17
- L-a｜refs/verify.csv（43 行，三列已核查填完）+ refs/missing_mentions.md + refs/verify_summary.md；refs/thesis.bib 扩至 64 篇｜2026-11-17

## 阻塞与待决定
- AutoDL 余额待释放（不阻塞本机工作，S1-a 等 CPU 任务可先行）

## 明天先做
- S0-a 校验冻结数据并打 tag data-v1
- S1-a 统一评估入口 eval/
