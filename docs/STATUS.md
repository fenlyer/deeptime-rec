# STATUS
当前周：W1（11/16–11/22） 本周关口：G1（11/21）

## 进行中
- RecBole 结合方案已确认（见 decisions.md 2026-11-17），adapter 与对账校验待实现（S1-b）

## 已完成（卡片 ID｜commit｜日期）
- W0-a｜仓库骨架与规则（CLAUDE.md、6 个命令、58 张卡片、目录与 README、Makefile 骨架）｜2026-11-16
- W0-b｜三样外部信息已确认（送审截止 2027-06、CNKI TMLC2 ≤10%/15%、AIGC ≤10%、模板已放入 thesis/template/）｜2026-11-17
- W0-c｜AutoDL 环境已选定（RTX 4090 / 数据盘 50G），待余额释放后完成 backup.sh 与 queue.sh｜2026-11-17

## 阻塞与待决定
- W0-c 残余：AutoDL 余额待释放，晚间确认实例；scripts/backup.sh 与 experiments/queue.sh 待写

## 明天先做
- S0-a 校验冻结数据并打 tag data-v1（依赖 W0-c AutoDL 可用）
- L-a 生成 refs/verify.csv 骨架（手工核查可同步开始）
