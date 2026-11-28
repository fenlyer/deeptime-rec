# STATUS

当前周：W2（11/27–12/3） 本周关口：G2
最后更新：2026-11-28

## 进行中

- S-recall-main（TI-LightGCN）：下一步

## 已完成（卡片 ID｜commit｜日期）

- W0-a｜仓库骨架与规则（CLAUDE.md、6 个命令、58 张卡片、目录与 README、Makefile 骨架）｜2026-11-16
- W0-b｜三样外部信息已确认（送审截止 2027-06、CNKI TMLC2 ≤10%/15%、AIGC ≤10%、模板已放入 thesis/template/）｜2026-11-17
- W0-c｜数据盘确认（RTX 4090 / 数据盘 50G）；experiments/queue.sh 已完成；backup 简化为 git 追踪（删除 backup.sh 与 Makefile backup 目标）｜2026-11-17
- L-a｜refs/verify.csv（43 行，三列已核查填完）+ refs/missing_mentions.md + refs/verify_summary.md；refs/thesis.bib 扩至 64 篇｜2026-11-17
- S0-a｜冻结数据校验通过，CHECKSUMS + tag data-v1（四数据集规模与 stats.json 一致）｜7e38f2a｜2026-11-17
- S0-b｜IS 数据画像完成：γ₀=0.0313/天（ln2/22.1天）、λ₀=0.000456/天（ln2/1520.5天）；5 张画像图（SVG+600dpi PNG）；规模与 stats.json 一致｜f83a40f｜2026-11-17
- S0-b 补｜TH、OP 画像 JSON 补跑完成（TH γ₀=0.026254/λ₀=0.000413；OP γ₀=0.030499/λ₀=0.000356）；规模断言均与 stats.json 一致｜914c491｜2026-11-18
- S1-a｜统一评估入口 eval/（metrics.py Recall/NDCG + full_rank.py 全排序/屏蔽/悲观并列 + eval.yaml + 10 个测试）｜b67994e｜2026-11-17
- S1-b｜RecBole 冒烟与冻结切分对接：environment/recbole.yml（Python 3.10 / torch 2.5.1+cu121 / recbole 1.2.1 / scipy 1.11.4 / numpy 1.26.4）、scripts/export_recbole.py、eval/crosscheck_recbole.py、configs/recbole_baselines.yaml、tests/test_verify_recbole_adapter.py（对账 1✅ 对账 2✅ 对账 3 skip 口径差异 对账 4 skip 已推迟）；LightGCN smoke 10 epochs 完成（checkpoint 已保存）；对账 4（PyG LightGCN 对比）推迟到后期（2026-11-19 决策）｜2026-11-19
- S1-c｜运行记录、配对检验、分层守恒：代码与测试已完成；eval/paired_test.py、eval/strata.py（四层口径：0-4/5-9/10-29/≥30，与论文表 3-11 对齐）｜23990e2 + 4c12842｜2026-11-18 / 2026-11-20
- S1-d｜数字管线：scripts/make_tables.py → thesis/generated/numbers.json（84 个 key，source 指向真实文件）｜4c12842｜2026-11-20
- G1 基础设施｜docs/plan/gates.md（V9 版 G1–G5 关口条件）、gates/w1.py（182 行，覆盖 G1 七条）｜4c12842｜2026-11-20
- E0-a / G1-7｜docs/prototype_inventory.md（G1 条件 7 产物；列出 backend/ 现状与论文第五章差距）｜4c12842｜2026-11-20
- V9 复核与论文待手动修改清单｜docs/revision/、decisions.md 末条：3.5.4/3.5.9/5.5.5 节须删、3.6 节改写、5.5 节总览改写、5.2.2 引用改写、1.3.3 创新点改写、5.6 截图图注标注「演示数据」｜4c12842｜2026-11-20
- S-recall-base（代码部分）｜runner 与配置完成、CPU 冒烟通过：experiments/run_recall_baseline.py、configs/recall/{bprmf,ngcf,lightgcn,sgl,simgcl}.yaml、experiments/make_baseline_summary.py、tests/test_recall_baseline_runner.py（29 个测试）；queue.txt 已挂 25 run + summary；autodl/S-recall-base.md 操作步骤；修复 common/run.py 的 manifest extra 覆盖 bug（+测试）。冒烟 BPR/seed0/2epoch 跑通，50985 用户全覆盖，604s→78s（按批算 + eval_batch_size 调整）｜2026-11-27
- S-recall-base（正式 25 run）｜25 个 run 全部完成（5 模型 × 5 seed），summary.csv 已生成；G1-6 解除｜c9026d6｜2026-11-27
- S-recall-base R1-R2（训练过程数据补全）｜runner 增加 per-epoch 计时/验证值/峰值显存/图构建耗时记录；旧结果归档至 `_archive/v1-20261127/`；25 run 重跑完成，D1-D4 数据齐全（train_log 四列、epoch_seconds、peak_memory_mb、build_seconds）。准确率与 archive 有微小差异（<10% 相对变化，论文结论不变），接受为新基线｜2dec68d｜2026-11-28

## 阻塞与待决定

- （无）G1 七条全部通过，进入 W2。

## 接下来（W2）

- S-recall-main：TI-LightGCN 实现与训练
