# STATUS
当前周：W1（11/16–11/22） 本周关口：G1（11/21）

## 进行中
- S1-c 运行记录、配对检验、分层守恒：代码与测试已完成（54 passed, 4 skipped），待提交

## 已完成（卡片 ID｜commit｜日期）
- W0-a｜仓库骨架与规则（CLAUDE.md、6 个命令、58 张卡片、目录与 README、Makefile 骨架）｜2026-11-16
- W0-b｜三样外部信息已确认（送审截止 2027-06、CNKI TMLC2 ≤10%/15%、AIGC ≤10%、模板已放入 thesis/template/）｜2026-11-17
- W0-c｜数据盘确认（RTX 4090 / 数据盘 50G）；experiments/queue.sh 已完成；backup 简化为 git 追踪（删除 backup.sh 与 Makefile backup 目标）｜2026-11-17
- L-a｜refs/verify.csv（43 行，三列已核查填完）+ refs/missing_mentions.md + refs/verify_summary.md；refs/thesis.bib 扩至 64 篇｜2026-11-17
- S0-a｜冻结数据校验通过，CHECKSUMS + tag data-v1（四数据集规模与 stats.json 一致）｜7e38f2a｜2026-11-17
- S0-b｜IS 数据画像完成：γ₀=0.0313/天（ln2/22.1天）、λ₀=0.000456/天（ln2/1520.5天）；5 张画像图（SVG+600dpi PNG）；规模与 stats.json 一致｜f83a40f｜2026-11-17
- S0-b 补｜TH、OP 画像 JSON 补跑完成（TH γ₀=0.026254/λ₀=0.000413；OP γ₀=0.030499/λ₀=0.000356）；规模断言均与 stats.json 一致｜914c491｜2026-11-18
- S1-a｜统一评估入口 eval/（metrics.py Recall/NDCG + full_rank.py 全排序/屏蔽/悲观并列 + eval.yaml + 10 个测试）｜b67994e｜2026-11-17
- S1-b｜RecBole 冒烟与冻结切分对接：environment/recbole.yml、scripts/export_recbole.py、eval/crosscheck_recbole.py、configs/recbole_baselines.yaml、tests/test_verify_recbole_adapter.py；对账 1 通过（.inter 文件行数与 ID 集合一致），对账 2-4 待 AutoDL 运行后校验｜2026-11-18

## 阻塞与待决定
- AutoDL 余额待释放（不阻塞本机工作，S1-b 之外的可先做）
- S1-b 前置：本机 `recbole_env` 缺 `recbole_gnn`（ModuleNotFoundError），SimGCL 侧需先装

## 接下来（G1 剩余）
- S1-b RecBole 冒烟与冻结切分对接 → crosscheck.json（G1 条件 4）
- S1-d 表格与数字管线骨架（依赖 S1-c）
- E0-a 原型现状表 → docs/prototype_inventory.md（G1 条件 6）
- T-a 论文源迁移与 smoke.docx（G1 条件 7；本机缺 pandoc，需先装）
- gates/w1.py 尚未实现，/gate 1 时补