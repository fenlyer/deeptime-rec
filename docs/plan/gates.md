# 每周关口

由 /gate N 读取。每个条件实现为 gates/wN.py 中的一个函数，输出 PASS / FAIL / MANUAL、实际值与证据路径。

## G1 评估地基（11/21 周六） 导师同步
- [ ] data-v1 tag 存在，sha256sum -c data/CHECKSUMS.sha256 全部 OK
- [ ] pytest tests/ 全过（eval、run、paired_test、strata、make_tables）
- [ ] 同一打分重复评估两次，per_user.parquet 的 sha256 相同
- [ ] crosscheck.json：四个指标差 < 1e-4，rank 一致率 ≥ 99.9%
- [ ] results/profile/IS.json 含 γ0、λ0、评分全相同比例、测试物品训练覆盖率；5 张图存在
- [ ] docs/prototype_inventory.md 存在
- [ ] refs/verify.csv 有 43 行
- [ ] build/smoke.docx 已生成，公式对象经你在 Word 中确认

不过时：G1 不过不开始 W2 的正式实验。最多占用 2 天，时间从 W2 的调参网格里扣（网格减半）。

## G2 基线（11/28 周六）
- [ ] results/recall_main/ 下 5 模型 × 5 seed 的 metrics.json 与 manifest.json 齐全
- [ ] 每个 run：best_epoch ≥ 30 且停止原因为耐心耗尽
- [ ] 测试目标口径写入 docs/预处理口径冻结.md、docs/decisions.md、configs/eval.yaml，三处一致
- [ ] rank/ 防泄漏测试通过；DIN smoke AUC > 0.5
- [ ] 旧原型在 serving/ 中可启动
- [ ] refs/verify.csv 每行都有你的核查结论

不过时：早停太早时查学习率与早停指标，重跑受影响的模型；不改耐心阈值去"通过"。

## G3 TI-LightGCN 主实验（12/05 周六） 导师同步
- [ ] tests/test_ti_lightgcn.py 三项通过（等价性、命题 1、命题 2）
- [ ] results/recall_ti/ 下 7 配置 × 5 seed 齐全
- [ ] gate_G3.json 中 p < 0.05 则通过；否则记录 Plan B 已启动（S3-pb）
- [ ] test_consistency.py --version v0 通过

不过时：不显著不是失败，是信号：当周启动 S3-pb，并把结论同步给导师。

## G4 召回收尾与冻结（12/12 周六）
- [ ] results/strata/recall.json 守恒校验通过
- [ ] results/cross/：3 数据集 × 3 模型 × 3 seed 齐全；tag data-v1-sub 存在
- [ ] figures/sens/ 下 5 张图；效率表生成
- [ ] tag recall-freeze 存在；ti_top100.parquet 与 coverage.json 存在
- [ ] artifacts/v1/manifest.json 的离线指标与 numbers.json 中对应值一致；test_consistency v1 通过

不过时：守恒不过通常是分层用错了人数口径（用了含测试的交互数）；修脚本，不调阈值。

## G5 LLM 教师离线部署（12/19 周六）
- [ ] user_memory.jsonl 覆盖用户数等于计划数；check_leak 0 命中
- [ ] results/llm/memory_review.csv 50 条人工判断已填
- [ ] teacher_quality.json（AUC、GAUC、ECE）与可靠性图存在
- [ ] results/rank_base/ 下 4 模型 × 5 seed 齐全
- [ ] 3 名标注者已确认时间（人工项）

不过时：vLLM 太慢：先查前缀缓存与 Prompt 长度，再按 budget.json 的第二档抽样蒸馏用户（Memory 仍全量）。教师 AUC 低于 DIN：保留蒸馏实验，W6 按"正则化"解释并报告置信度加权的作用。

## G6 排序、端到端与 v2（12/26 周六） 导师同步
- [ ] tests/test_temporal_din.py 三项通过
- [ ] results/rank_main/、rank_ablation/ 5 seed 齐全；gate_G6.json 存在
- [ ] results/e2e/ 完整系统行存在，且断言"指标由最终列表计算"通过
- [ ] 完整系统 R@10 与单独召回阶段 R@10 不同；相同时给出逐用户解释
- [ ] test_consistency_v2 通过；tag artifacts-v2 存在

不过时：蒸馏无增益：如实报告，第 4 章贡献重心放到"时间偏置 + Memory 特征增强"，创新点表述相应收窄。端到端不如仅召回：扫候选规模 K ∈ {50, 100, 200}，报告召回覆盖率与排序命中率，不挑结果。

## G7 解释评估与系统测试（01/02 周六）
- [ ] results/explain/：属性一致率、LLM 评审、人工均值、Fleiss κ 齐全
- [ ] scripts/case.py 对 5 个案例重复运行输出一致
- [ ] 功能用例 15–25 条全部通过（junit 报告）
- [ ] locust 三场景结果、RSS 记录、env.json 存在
- [ ] figures/screens/ 下 5–8 张截图

不过时：κ < 0.4：如实报告并讨论；可以澄清细则后让标注者重标 20 对作为补充，不替换原结果。

## G8 冻结实验，算法章成稿（01/09 周六）
- [ ] tag exp-freeze 存在
- [ ] make thesis 对第 3、4 章 0 个未解析占位符
- [ ] check_thesis：第 3、4 章 0 个裸数字、0 个禁用词
- [ ] 全部实验图为 SVG 或 600dpi PNG，字体字号统一

不过时：裸数字逐个改成占位符；找不到来源的数字删除，或者补跑后再用。

## G9 V9 全文初稿（01/16 周六） 导师同步
- [ ] build/thesis_V9.docx 生成
- [ ] check_refs：0 缺失 key、0 未引用、0 缺 DOI/URL、编号单调
- [ ] 中英文摘要、附录齐全
- [ ] 全文 check_thesis：0 未解析占位符、0 裸数字、0 禁用词

不过时：写作延误时先保证第 3、4、5 章完整，第 1、2 章可以带少量待改标记交导师，W10 前两天补完。

## G10 审校与送审稿（01/24 周日） 导师同步
- [ ] final_checklist.md 中 22 项全部勾选且有证据
- [ ] 查重与 AIGC 自检低于学院阈值，报告存档
- [ ] anonymity.md 0 命中
- [ ] 导师审阅意见已处理或记录在 docs/advisor/tracker.md

不过时：任何一项不过都不送审；用缓冲周处理。
