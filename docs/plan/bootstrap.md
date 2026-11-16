# bootstrap.md
由《硕士论文整改执行计划》导出，生成于 2026-11-15。
交给 Claude Code：按“=== FILE: 路径 ===”分隔写出各文件（见任务卡 W0-a）。

=== FILE: CLAUDE.md ===
# 项目：工业品推荐硕士论文（deeptime-rec）

本仓库同时承载论文实验、原型系统和论文源文件。
执行计划：docs/plan/（任务卡 cards/、关口 gates.md）。当前进度：@docs/STATUS.md
口径：@docs/口径冻结.md　　决策记录：docs/decisions.md

## 红线
1. 不修改 data/processed/、data/CHECKSUMS.sha256、docs/口径冻结.md。数据或口径需要变化时停下来问我，由我决定并记入 docs/decisions.md。
2. 论文中的实验数字只能来自 thesis/generated/numbers.json（由 scripts/make_tables.py 从 results/ 生成），正文用 {{n:key}} 引用。不手写、不估计、不取整美化任何结果数字。
3. 不为改善指标修改 eval/、configs/eval.yaml、切分或屏蔽规则。评估代码的任何改动先说明原因，等我确认。
4. 验证集只用于早停与选参；测试集只在最终评估读取。不在测试集上调参，不挑 seed。
5. 不生成、不补全参考文献条目（作者、标题、DOI、页码）。refs/thesis.bib 只由我从 Zotero 导出。
6. 论述、分析、结论段落由我执笔。你负责列事实清单、核对数字与代码一致性、指出问题、做结构与格式修改。我明确说“起草”时，草稿写到 thesis/drafts/，不直接写入 thesis/src/。
7. 结果异常时先列出可能原因和验证办法，不要直接改代码去“修好”结果。

## 运行规范
- 每次训练或评估都经 common/run.py 记录到 results/{exp}/{model}/seed{n}/：metrics.json、per_user.parquet、config.yaml、train_log.csv、manifest.json。
- 工作区有未提交改动时不启动正式实验；smoke 实验放 results/_smoke/。
- 预计超过 10 分钟的任务：写成脚本，追加到 experiments/queue.txt，由 queue.sh 在 tmux 后台执行；告诉我日志路径，不在会话里等待。
- 只用训练集建图、训练、生成 User Memory。原型演示版例外，manifest 中 data_scope 必须写 full_history。
- seed 取 0–4；主结果 5 个 seed，敏感性与跨域 3 个 seed。

## 代码规范
- 先写或更新测试，再实现；pytest 全过才算完成。评估、边权、注意力、损失函数必须有数值测试。
- 边权构造、ID 映射、样本构造各只有一个实现，其他地方复用，不复制。
- commit message 以任务卡 ID 开头，例如 “S1-a: 统一全排序评估”。
- 改动 eval/、data/、configs/eval.yaml 时，在回复开头单独提醒我。

## 常用命令
make test                    # 全部测试
make gate W=3                # 第 3 周关口检查（python -m gates.w3）
make tables                  # results/ → thesis/generated/
make thesis [AUDIT=1]        # 生成 build/thesis_V9.docx（AUDIT=1 时数字后附来源）
make artifacts V=v1 ...      # 导出原型产物
make backup                  # 备份结果与论文源

## 环境（按实际修改）
- GPU：AutoDL RTX 4090 24GB，16 vCPU / 60 GB；数据盘 /root/autodl-tmp
- conda 环境：rec（RecBole）、llm（vLLM）、serve（原型，uv 锁定）

## 符号约定（论文与代码一致）
λ 图时间衰减率；λ₂ L2 正则；μ 长尾正则强度；α_r 反馈强度；a_k 注意力权重；
γ 注意力时间衰减率；η 蒸馏损失权重；ρ 语义重排权重；τ 蒸馏温度；时间单位为天（Δ_day = 86400 s）。

## 论文源 thesis/src/
- Markdown 正文；公式用 LaTeX（$…$ / $$…$$）；引用 [@key]；数字 {{n:key}}；表格 {{table:name}}。
- 禁用词：首次、填补空白、创造性地、范式性突破、彻底解决、值得注意的是、充分体现了。

## 目录
data/ 冻结数据与预处理　common/ 运行记录　eval/ 统一评估与统计　configs/ 全部配置
models/ 召回模型　rank/ 排序模型与样本　llm/ 教师与 Memory　experiments/ 复现脚本与队列
results/ 结果　gates/ 每周关口检查　export/ 产物导出　artifacts/ 原型产物　serving/ 原型后端　tests/ 测试
scripts/ 表、图、论文构建与检查　refs/ 文献　thesis/ 论文源　docs/ 计划、决策、周报

=== FILE: .claude/commands/card.md ===
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

=== FILE: .claude/commands/gate.md ===
---
description: 运行第 N 周关口检查
argument-hint: <周次数字，如 3>
---
检查第 $ARGUMENTS 周关口是否通过。
1. 若 gates/w$ARGUMENTS.py 不存在：按 docs/plan/gates.md 中 G$ARGUMENTS 的条件实现它。每个条件一个函数，输出 PASS/FAIL、实际值和证据文件路径；人工确认项输出 MANUAL。检查必须读取真实产物，不允许为通过而放宽阈值。
2. 运行 python -m gates.w$ARGUMENTS，原样贴出输出。
3. 对每个 FAIL，给出最可能的 2–3 个原因和验证办法，不要动手修。
4. 把结果写入 docs/weekly/G$ARGUMENTS.md，并更新 docs/STATUS.md。

=== FILE: .claude/commands/weekly.md ===
---
description: 生成给导师的周报草稿
argument-hint: <周次数字>
---
根据本周 git log、docs/STATUS.md、docs/weekly/G$ARGUMENTS.md 和 docs/decisions.md，生成 docs/weekly/W$ARGUMENTS.md：
本周完成（卡片 ID 与产出路径）；关口结果；关键数字（只能引用 numbers.json 的 key 与值）；遇到的问题与已做的决定；下周计划；需要导师决定的事项。
一页以内，不加评价性形容词。

=== FILE: .claude/commands/trace.md ===
---
description: 追溯论文中一个数字的来源
argument-hint: <数字或 numbers.json 的 key>
---
在 thesis/src/、thesis/generated/numbers.json、results/ 中查找 “$ARGUMENTS”：
给出它在论文中的全部位置、对应的 key、来源文件、生成命令、manifest 中的 git commit 与 data tag。
如果它是裸数字（不经占位符）或找不到来源，明确标为“无来源”，并列出可能对应的结果文件。

=== FILE: .claude/commands/thesis-check.md ===
---
description: 论文一致性检查（只报告，不改正文）
---
运行 scripts/check_thesis.py 与 scripts/check_refs.py，再补充脚本难以发现的问题：
- 未解析的占位符；正文中不经占位符出现的实验数字；
- 禁用词与评价性套话（列出位置）；
- 与 thesis/src/symbols.md 冲突的符号；公式、图、表编号是否连续；
- 引用 key 不在 bib、bib 中有未引用条目、条目缺 DOI/URL；
- 同一事实前后不一致（向量维度、矩阵规模、MLP 结构、并发数、延迟、内存）；
- 论文描述与代码不一致（以代码和配置为准，附文件:行号）。
输出 docs/weekly/thesis_check_<日期>.md，按章节排序。不修改 thesis/src/。

=== FILE: .claude/commands/exp.md ===
---
description: 新建一个实验的脚手架
argument-hint: <实验名> <模型名> <数据集>
---
为实验 $ARGUMENTS 创建：configs/ 下的配置文件、experiments/ 下的一键运行脚本（接受 seed 参数）、results/ 下的目标路径约定，并把 5 个 seed 的命令追加到 experiments/queue.txt（先不执行）。
运行脚本必须经 common/run.py 记录，测试集评估必须调用 eval/ 的统一入口。完成后列出新文件与队列中新增的命令，等我确认再启动队列。

=== FILE: docs/STATUS.md ===
# STATUS
当前周：W1（11/16–11/22）　本周关口：G1（11/21）

## 进行中
- 

## 已完成（卡片 ID｜commit｜日期）
- W0-a｜｜

## 阻塞与待决定
- 

## 明天先做
-

=== FILE: docs/decisions.md ===
# 决策记录
格式：日期｜决定｜理由｜影响的文件或章节｜是否要改论文

- 2026-11-15｜采用执行计划 V1（W1 = 2026-11-16）｜—｜全部｜—

=== FILE: docs/ai_usage.md ===
# AI 工具使用记录
按学校要求填写。每条：日期｜工具｜用途（代码 / 检查 / 格式 / 草稿）｜涉及的文件｜我如何核对

-

=== FILE: docs/plan/gates.md ===
# 每周关口

由 /gate N 读取。每个条件实现为 gates/wN.py 中的一个函数，输出 PASS / FAIL / MANUAL、实际值与证据路径。

## G1 评估地基（11/21 周六）　导师同步
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
- [ ] 测试目标口径写入 docs/口径冻结.md、docs/decisions.md、configs/eval.yaml，三处一致
- [ ] rank/ 防泄漏测试通过；DIN smoke AUC > 0.5
- [ ] 旧原型在 serving/ 中可启动
- [ ] refs/verify.csv 每行都有你的核查结论

不过时：早停太早时查学习率与早停指标，重跑受影响的模型；不改耐心阈值去“通过”。

## G3 TI-LightGCN 主实验（12/05 周六）　导师同步
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

不过时：vLLM 太慢：先查前缀缓存与 Prompt 长度，再按 budget.json 的第二档抽样蒸馏用户（Memory 仍全量）。教师 AUC 低于 DIN：保留蒸馏实验，W6 按“正则化”解释并报告置信度加权的作用。

## G6 排序、端到端与 v2（12/26 周六）　导师同步
- [ ] tests/test_temporal_din.py 三项通过
- [ ] results/rank_main/、rank_ablation/ 5 seed 齐全；gate_G6.json 存在
- [ ] results/e2e/ 完整系统行存在，且断言“指标由最终列表计算”通过
- [ ] 完整系统 R@10 与单独召回阶段 R@10 不同；相同时给出逐用户解释
- [ ] test_consistency_v2 通过；tag artifacts-v2 存在

不过时：蒸馏无增益：如实报告，第 4 章贡献重心放到“时间偏置 + Memory 特征增强”，创新点表述相应收窄。端到端不如仅召回：扫候选规模 K ∈ {50, 100, 200}，报告召回覆盖率与排序命中率，不挑结果。

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

## G9 V9 全文初稿（01/16 周六）　导师同步
- [ ] build/thesis_V9.docx 生成
- [ ] check_refs：0 缺失 key、0 未引用、0 缺 DOI/URL、编号单调
- [ ] 中英文摘要、附录齐全
- [ ] 全文 check_thesis：0 未解析占位符、0 裸数字、0 禁用词

不过时：写作延误时先保证第 3、4、5 章完整，第 1、2 章可以带少量待改标记交导师，W10 前两天补完。

## G10 审校与送审稿（01/24 周日）　导师同步
- [ ] final_checklist.md 中 22 项全部勾选且有证据
- [ ] 查重与 AIGC 自检低于学院阈值，报告存档
- [ ] anonymity.md 0 命中
- [ ] 导师审阅意见已处理或记录在 docs/advisor/tracker.md

不过时：任何一项不过都不送审；用缓冲周处理。

=== FILE: docs/plan/cards/W0-a.md ===
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

=== FILE: docs/plan/cards/W0-b.md ===
# W0-b 拿到三样外部信息

- 周次：W0 启动日（11/15 周日（最迟 11/16 上午完成））
- 线：事务
- 估时：1 小时

## 说明
向导师确认送审截止日；下载北邮研究生院当年发布的学位论文 Word 模板；查清学院本年度查重与 AIGC 检测用的平台和阈值。三样都写进 docs/decisions.md。截止日早于 2027-01-24 时，按“关口与 Plan B”一节的压缩规则调整，关口不删。

## 产出
docs/decisions.md 中 3 条记录；thesis/template/ 下的学校模板

## 验收
三条记录齐全，模板文件可以打开

## 论文落点
决定第 5 周以后的写作格式

=== FILE: docs/plan/cards/W0-c.md ===
# W0-c 数据盘、备份与后台任务队列

- 周次：W0 启动日（11/15 周日（最迟 11/16 上午完成））
- 线：事务
- 估时：1 小时

## 提示词

在 AutoDL 实例上：
1. 确认数据盘路径（如 /root/autodl-tmp），把 processed/、artifacts/ 和体积大的结果文件放在数据盘，仓库内用软链接；把实际路径写进 CLAUDE.md 的“环境”一节。
2. 写 scripts/backup.sh：把 results/ 下所有 metrics.json 与 manifest.json、artifacts/*/manifest.json、thesis/、refs/、docs/ 同步到备份位置（我会告诉你是网盘还是本地机器），加进 Makefile 的 backup 目标。
3. 写 experiments/queue.sh：逐行读取 experiments/queue.txt 中的命令，在 tmux 会话 exp 中顺序执行，每条结束后向 experiments/queue.log 追加开始时间、结束时间、退出码；已执行过的行加前缀 # done 。
用两条 echo 测试命令验证队列，然后停下。

## 产出
scripts/backup.sh；experiments/queue.sh；Makefile 的 backup 目标

## 验收
make backup 成功一次；queue.log 中两条测试命令退出码为 0

## 论文落点
无

=== FILE: docs/plan/cards/S0-a.md ===
# S0-a 校验冻结数据并打 tag

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：0.5 天

## 提示词

运行 data/ 下的 verify_loo.py 和三个 verify_*.py，输出保存到 results/verify/。
任何一项失败就停下，报告失败内容，不要修改数据或脚本去“让它通过”。
全部通过后：
1. 为 data/processed/{IS,TH,OP,AJ}/ 下每个文件计算 sha256，写入 data/CHECKSUMS.sha256 并提交；
2. 打 git tag data-v1；
3. 在 docs/decisions.md 记一条：日期、tag、四个数据集的用户数/物品数/交互数（从 stats.json 读，不手填）。

## 产出
results/verify/；data/CHECKSUMS.sha256；tag data-v1

## 验收
sha256sum -c data/CHECKSUMS.sha256 全部 OK；git tag 中有 data-v1

## 论文落点
第 3 章数据集小节的预处理与切分说明

=== FILE: docs/plan/cards/S0-b.md ===
# S0-b 数据画像与 γ₀、λ₀

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S0-a

## 提示词

写 scripts/profile_data.py，只读 data/processed/IS/，输出 results/profile/IS.json 和 figures/profile/ 下 5 张图：
评分分布；用户训练交互数分布（对数坐标）；用户内相邻交互间隔分布（单位天，对数坐标）；测试物品是否在训练集出现过的比例；用户内评分是否全部相同的比例。
JSON 另外给出：相邻间隔中位数（天）、训练集交互年龄中位数（以训练集最大时间戳为参照，天）、由它们算出的 γ0 = ln2 / 间隔中位数、λ0 = ln2 / 年龄中位数，每个数字附一句计算口径。
图同时导出 SVG 和 600dpi PNG，中文宋体、西文 Times New Roman，字号 10.5pt，样式写成 scripts/plot_style.py 供以后所有图复用。
脚本末尾断言用户数、物品数、交互数与 stats.json 一致。TH、OP 只算 JSON 不画图。

## 产出
results/profile/{IS,TH,OP}.json；figures/profile/*.svg|png；scripts/plot_style.py

## 验收
JSON 字段齐全；5 张图存在；断言通过

## 论文落点
第 3 章数据集小节、数据画像图；γ 和 λ 取值依据（替代 V8 的 γ=0.3、λ=0.001 经验值）

=== FILE: docs/plan/cards/S1-a.md ===
# S1-a 统一评估入口 eval/

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：1 天

## 提示词

在 eval/ 下实现统一评估，先写测试再写实现：
- metrics.py：给定每个用户测试物品的排名，计算 Recall@K（LOO 下等于 HR@K）与 NDCG@K（IDCG=1），K ∈ {10, 20}。
- full_rank.py：输入用户与物品嵌入（或一个打分函数），对全部物品打分，屏蔽该用户的训练和验证物品，输出 per_user.parquet，列为 user_id, test_item, rank, test_item_in_train, test_rating。
- 并列分数取悲观排名（与测试物品同分的物品都算排在它前面），在 docstring 写清楚。
- 支持两种测试目标口径：--target all（全部测试目标）与 --target pos（只评 rating≥4 的目标），默认值从 configs/eval.yaml 读取。
tests/test_eval.py：3 个用户、6 个物品的手算样例，覆盖屏蔽、并列、K 边界、两种口径。
另写一个检查：同一份打分评估两次，per_user.parquet 的 sha256 必须相同。pytest 全过后给我看。

## 产出
eval/metrics.py；eval/full_rank.py；configs/eval.yaml；tests/test_eval.py

## 验收
pytest tests/test_eval.py 全过；重复评估 hash 一致

## 论文落点
评价指标公式改写为 LOO 化简形式（式 5-1 的替代），“全排序、屏蔽训练与验证物品”的说明

=== FILE: docs/plan/cards/S1-b.md ===
# S1-b RecBole 冒烟测试与冻结切分对接

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：1 天
- 依赖：S0-a、S1-a

## 提示词

目标：确认 RecBole 与 RecBole-GNN 能在本机运行，并且读取我们冻结好的切分，而不是让它自己切。
1. 在独立 conda 环境中安装 RecBole 与 RecBole-GNN，用自带小数据集跑 LightGCN 1 个 epoch。若与 Python 3.12 / PyTorch 2.4 不兼容，新建 Python 3.10 环境；把选择和全部版本号写入 environment/recbole.yml 与 docs/decisions.md。
2. 写 data/to_recbole.py：把 processed/IS 的 train/val/test 转成 RecBole atomic 文件，用 benchmark_filename 方式加载，字段含 user_id、item_id、rating、timestamp。
3. LightGCN 在 IS 上训练（seed 0，可先少轮数），同一个 checkpoint 分别用 RecBole 自带评估和 eval/full_rank.py 评估。
4. 写 eval/crosscheck_recbole.py，比较两边 Recall@10/20、NDCG@10/20 的差值和逐用户 rank 一致的比例。
不一致时先查屏蔽规则（测试时是否屏蔽训练+验证物品）与 ID 映射，不要改 eval/ 去迁就 RecBole。

## 产出
environment/recbole.yml；data/to_recbole.py；eval/crosscheck_recbole.py；results/_smoke/crosscheck.json

## 验收
四个指标差值 < 1e-4，且 ≥ 99.9% 用户 rank 一致；不一致的用户逐个说明原因

## 论文落点
第 3 章实验设置：基线实现来源（RecBole，CIKM 2021）

=== FILE: docs/plan/cards/S1-c.md ===
# S1-c 运行记录、配对检验、分层守恒

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S1-a

## 提示词

1. common/run.py：start_run(exp, model, seed, config) 创建 results/{exp}/{model}/seed{n}/；结束时写 manifest.json：git commit、工作区是否有未提交改动、data tag、完整命令、开始与结束时间、GPU 型号、峰值显存、每轮耗时列表、best_epoch、停止原因（耐心耗尽/最大轮数）。工作区不干净时打印醒目警告，并把结果目录前缀改为 _dirty_。
2. eval/paired_test.py：输入两个模型的结果目录（多个 seed），先对每个用户在各 seed 上取平均，再做配对 t 检验与 Wilcoxon 符号秩检验；输出 n、均值差、t、p、d_z = t/√n、Wilcoxon p，写成 JSON。
3. eval/strata.py：按训练集交互数分 3–4 / 5–9 / 10–29 / ≥30 四层，输出各层指标与人数；断言按人数加权的均值与整体指标之差 < 1e-9。
每个脚本配 pytest（paired_test 用构造数据验证 d_z 公式）。

## 产出
common/run.py；eval/paired_test.py；eval/strata.py；对应测试

## 验收
pytest 全过；对一个 smoke 结果目录能生成 manifest.json

## 论文落点
显著性检验方法（以用户为单位，替代 V8 5.5.3 的 t(4) 检验）；冷启动分层口径

=== FILE: docs/plan/cards/S1-d.md ===
# S1-d 表格与数字管线骨架

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S1-c

## 提示词

写 scripts/make_tables.py 与 scripts/build_thesis.py 的骨架（格式见执行计划附录 D）：
- make_tables.py 读取 results/ 下的 metrics.json（多 seed 汇总为均值±标准差），按 configs/tables.yaml 的定义生成 thesis/generated/tables/{name}.md，并把每个单元格登记进 thesis/generated/numbers.json：key → {value, display, sources, command, commit, data_tag}。显著性标记由 paired_test 的 JSON 决定，不手写。
- build_thesis.py 把 thesis/src/*.md 中的 {{n:key}} 与 {{table:name}} 替换为实际内容，输出 build/thesis.md；遇到不存在的 key 报错退出；--audit 模式在每个数字后追加〔来源文件〕。
- scripts/check_thesis.py：列出未解析的占位符、正文中不经占位符出现的小数或百分数、禁用词。
现在 results/ 里没有正式结果：用 tests/fixtures/ 下的假结果目录测试，fixtures 里的数字不能出现在 thesis/src/。

## 产出
scripts/make_tables.py；scripts/build_thesis.py；scripts/check_thesis.py；configs/tables.yaml

## 验收
对 fixtures 能生成表格与 numbers.json；缺 key 时报错退出

## 论文落点
之后所有表格与正文数字的唯一来源

=== FILE: docs/plan/cards/E0-a.md ===
# E0-a 原型现状表

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：工程线
- 估时：0.5 天

## 提示词

原型代码在 <原型路径>。逐个模块读代码，不运行、不修改，产出 docs/prototype_inventory.md，一张表：
模块 | 文件 | 用到的模型或产物文件 | 产物如何生成、基于什么数据口径（是否 SNAP v1、比例切分、旧规模嵌入） | 对外接口 | 论文中对应的描述位置（V8 章节号） | 与论文描述是否一致。
与 docs/口径冻结.md 不一致的项标 ⚠️。
最后单列两张清单：“论文写了但代码里没有”（如 MySQL binlog、Redis RDB/AOF、IVF-PQ），“代码里有但论文没写”。

## 产出
docs/prototype_inventory.md

## 验收
每个模块一行；两张清单非空或写明“无”

## 论文落点
第 5 章“目标架构 / 原型实现”对照表的素材

=== FILE: docs/plan/cards/L-a.md ===
# L-a 43 条文献核查表

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：写作线
- 估时：1 天（跨 W1–W2，主要是你手工核查）

## 提示词

从 thesis/v8_md/ 抽出参考文献列表和正文中每个 [n] 的出现位置，生成 refs/verify.csv，列为：
编号 | 原条目 | 首次出现的章节与所在句 | 全部出现位置 | 路线图核查结论（照抄 docs/revision/论文整改路线图 的文献表，没有就留空） | 路线图处理建议 | DOI/链接 | 我的核查结论 | 核查日期。
最后三列留空。不要自己补 DOI、作者、页码，也不要推荐替代文献：这些由我在 DBLP/知网逐条核对后填写。
另外列出“正文提到但没有文献条目”的模型名或数据集名，写到 refs/missing_mentions.md。

## 产出
refs/verify.csv；refs/missing_mentions.md

## 验收
43 行齐全；你逐条填完后三列（W2 结束前）

## 论文落点
参考文献清理；第 1、2 章引用位置修正

=== FILE: docs/plan/cards/T-a.md ===
# T-a 论文源迁移到 Markdown，冒烟一次 Word 输出

- 周次：W1 评估地基（11/16 周一 – 11/22 周日）
- 线：写作线
- 估时：0.5 天
- 依赖：W0-b

## 提示词

1. 用 pandoc 把 docs/revision/整改V8_1112.docx 转成 Markdown（--extract-media=thesis/media），按章拆到 thesis/v8_md/ch1.md … ch7.md。这些文件只作参照，以后不改。
2. 按执行计划“论文改写流水线”一节的新结构，建立 thesis/src/00_front.md、01_intro.md、02_background.md、03_ti_lightgcn.md、04_temporal_din.md、05_system.md、06_conclusion.md、90_appendix.md、symbols.md 骨架：只放标题层级，每个小节下用注释写明素材来源，如 <!-- 素材: V8 4.1.2, 5.4.1 -->，正文留空。
3. 从 thesis/template/ 的学校模板生成 thesis/reference.docx（复制模板、清空正文、保留样式）。
4. 冒烟：写 thesis/smoke.md，含 1 个 LaTeX 公式、1 张 SVG 图、1 张 PNG 图、1 条 [@key] 引用，用 pandoc（reference-doc、citeproc、GB/T 7714 顺序编码 CSL）转成 build/smoke.docx。把命令写进 Makefile 的 smoke 与 thesis 目标。
我会用 Word 打开 smoke.docx 确认公式是公式对象、图片正常、引用格式正确。

## 产出
thesis/v8_md/；thesis/src/ 骨架；thesis/reference.docx；build/smoke.docx

## 验收
Word 中公式可点击编辑（公式对象）；SVG 在你的 Word 版本里能显示，否则以后统一用 PNG

## 论文落点
V9 的源文件；解决“文档中 0 个公式对象”

=== FILE: docs/plan/cards/S2-a.md ===
# S2-a 召回基线 × 5 seed

- 周次：W2 基线（11/23 周一 – 11/29 周日）
- 线：研究线
- 估时：1 天人工 + 约 1.5 GPU 天（夜间队列）
- 依赖：G1

## 提示词

用 RecBole/RecBole-GNN 跑召回基线 BPR-MF、NGCF、LightGCN、SGL、SimGCL，数据为 IS 冻结切分（benchmark_filename）。
- 统一设置：d=64，最大 1000 轮，按验证集 NDCG@20 早停，耐心 30；所有运行经 common/run.py 记录。
- 先在 seed 0 上对每个模型做小网格调参（学习率、L2、各自关键超参，每个模型不超过 8 组），只看验证集；选定后写进 configs/recall/{model}_IS.yaml，并在 docs/decisions.md 记录网格与选择。
- 再用 seed 0–4 各跑一次正式实验，测试集评估一律调用 eval/full_rank.py。
- 写 experiments/run_recall.sh <model> <dataset>，一条命令复现一行；把全部命令追加到 experiments/queue.txt，由 queue.sh 后台执行，不在会话里等待。
全部完成后检查：每个 run 的 best_epoch ≥ 30，停止原因为耐心耗尽；不满足的列出来，不要自行改早停规则。

## 产出
configs/recall/*.yaml；results/recall_main/{model}/seed{0..4}/；experiments/run_recall.sh

## 验收
25 个 run 齐全；早停检查全部通过；make_tables 能生成召回基线表

## 论文落点
第 3 章对比方法与主结果表（基线行）；附录超参数表

=== FILE: docs/plan/cards/S2-b.md ===
# S2-b 冻结测试目标口径

- 周次：W2 基线（11/23 周一 – 11/29 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S2-a 中 LightGCN 完成

## 提示词

用 LightGCN 5 个 seed 的 per_user.parquet，分别按“全部测试目标”和“仅 rating≥4 目标”计算 Recall@10/20、NDCG@10/20 和用户数，生成 results/target_policy/compare.json 与一张对比表。
不要替我做决定，把两种口径的用户数、指标和差异列出来。
我决定后：把决定写进 docs/口径冻结.md 第一节与 docs/decisions.md，在 configs/eval.yaml 固定默认口径，并说明另一种口径的结果放附录。

## 产出
results/target_policy/compare.json；更新后的口径冻结文件与 configs/eval.yaml

## 验收
口径写入三处且一致

## 论文落点
第 3 章实验设置：测试目标口径；附录：另一口径的结果

=== FILE: docs/plan/cards/S2-c.md ===
# S2-c 排序样本与排序评估框架

- 周次：W2 基线（11/23 周一 – 11/29 周日）
- 线：研究线
- 估时：1.5 天
- 依赖：S1-a

## 提示词

在 rank/ 下搭排序实验框架（不依赖 RecBole）：
- rank/samples.py：对训练集中每个用户的第 k 条交互（k ≥ 2）构造样本：历史 = 前 k−1 条（带时间戳），正样本 = 第 k 条；负样本 = 召回候选中的难负例 h 个 + 全库随机 r 个，h、r 写进 configs/rank/samples.yaml。候选文件路径作为参数；现在先用 LightGCN seed 0 导出的 Top-100 代替，W4 换成 TI-LightGCN。
- rank/eval_rank.py：给定每个测试用户的固定候选列表与打分，计算 AUC、GAUC、NDCG@10；--protocol isolated 时测试物品不在候选中则补入（日志记录补入比例），--protocol e2e 时不补入。
- rank/models/din.py：标准 DIN 作为第一个模型，seed 0 跑通。
- 测试：断言任何验证或测试物品都不出现在训练样本的正负样本与历史中；DIN smoke 的 AUC > 0.5 且训练损失下降。

## 产出
rank/samples.py；rank/eval_rank.py；rank/models/din.py；configs/rank/samples.yaml

## 验收
防泄漏测试通过；DIN smoke 结果写入 results/_smoke/din/

## 论文落点
第 4 章实验设置：样本构造、两套评估协议

=== FILE: docs/plan/cards/E0-b.md ===
# E0-b 原型代码迁入 serving/

- 周次：W2 基线（11/23 周一 – 11/29 周日）
- 线：工程线
- 估时：0.5–1 天
- 依赖：E0-a

## 提示词

把原型后端代码迁入 serving/（保留原仓库的 commit 号写在 serving/README.md），把 ID 映射改为读取 data/processed/IS/ 的统一映射文件。
本卡只要求旧原型在新位置能启动并返回结果，不改推荐逻辑、不换模型。
serving/README.md 写清启动命令、依赖、环境变量；依赖用 uv 锁定。

## 产出
serving/；serving/README.md

## 验收
按 README 启动后，对一个测试用户能返回推荐列表

## 论文落点
无（为 E1 做准备）

=== FILE: docs/plan/cards/L-b.md ===
# L-b 删改问题文献，补近三年工作

- 周次：W2 基线（11/23 周一 – 11/29 周日）
- 线：写作线
- 估时：1.5 天（你手工为主）
- 依赖：L-a

## 提示词

读 refs/verify.csv（我已填写结论的行）和 refs/thesis.bib（Zotero Better BibTeX 自动导出）。只做比对报告，写入 refs/coverage.md，不要写入或修改 bib：
1. bib 中每个 key 的 DOI/URL 是否为空；
2. 路线图“建议补充”表中的条目哪些还不在 bib 里（按标题比对，不生成条目）；
3. refs/missing_mentions.md 中每个名词当前是否已有 bib 条目；
4. verify.csv 中结论为“删除”的条目是否仍在 bib 里。

## 产出
refs/thesis.bib（你在 Zotero 中维护）；refs/coverage.md

## 验收
KAR、DLLM2Rec、RLMRec、孙浩然 2025 等最接近工作已入库且有 DOI/链接

## 论文落点
第 1 章 1.2 节、第 4 章与相关工作的区别

=== FILE: docs/plan/cards/S3-a.md ===
# S3-a TI-LightGCN 实现与命题测试

- 周次：W3 TI-LightGCN 主实验（11/30 周一 – 12/06 周日）
- 线：研究线
- 估时：1 天
- 依赖：S1-b、S0-b

## 提示词

在 models/ti_lightgcn.py 实现 TI-LightGCN，作为 RecBole 自定义模型（结构沿用 LightGCN）：
- 边权 w(u,i) = α_r · exp(−λ · (τ_u − t_ui) / Δ_day)，只用训练集交互。τ_u 支持 global（训练集最大时间戳）与 user（该用户训练集最后一次交互时间）两种。λ 默认取 results/profile/IS.json 的 λ0。
- α_r 由配置给出（只有比值有意义）；rating≤2 的处理支持 in_graph（权重 α_1,2）、drop（不入图，只作 BPR 硬负）、signed（先 raise NotImplementedError）。
- 归一化 Ã = D^(-1/2) A D^(-1/2)，D 为加权度。加权邻接的构造写成独立函数 build_weighted_adj()，以后 TI-SimGCL 复用。
- 长尾正则：固定投影（SBERT 384 维经 PCA 降到 64 维，一次性算好存文件）的余弦形式，系数记为 μ。
先写 tests/test_ti_lightgcn.py：
 (1) 所有边权为 1 时，传播结果与 RecBole LightGCN 逐元素相等（容差 1e-6）；
 (2) 边权整体乘常数 c 时 Ã 不变；global 时钟下改变 T_now，Ã 不变（命题 1）；
 (3) 小图上 Ã 的特征值都落在 [−1, 1]（命题 2）。
测试全部通过后再接入训练脚本。

## 产出
models/ti_lightgcn.py；tests/test_ti_lightgcn.py；artifacts_static/tail_pca64.npy

## 验收
三项测试通过

## 论文落点
第 3 章模型、命题 1 与 2；附录命题的数值验证

=== FILE: docs/plan/cards/S3-b.md ===
# S3-b 主实验、消融、变体 × 5 seed

- 周次：W3 TI-LightGCN 主实验（11/30 周一 – 12/06 周日）
- 线：研究线
- 估时：1 天人工 + 约 1 GPU 天
- 依赖：S3-a

## 提示词

用 configs/recall/ti_lightgcn_IS.yaml，在 seed 0 上做小网格调参（λ ∈ {0.5, 1, 2}×λ0、μ ∈ {1e-3, 1e-2}、α 比值两组），只看验证集，选定后记入 docs/decisions.md。
然后以下配置各跑 5 个 seed，结果放 results/recall_ti/{config}/：
完整；去反馈权重；去时间衰减；两者都去；去长尾正则；负反馈 drop；用户相对时钟。
全部完成后：
- 用 eval/paired_test.py 计算每个配置 vs LightGCN，以及完整 TI vs SimGCL；
- 生成 results/recall_ti/gate_G3.json：完整 TI 相对 LightGCN 在 R@10、N@10 上的均值差、p、d_z，以及是否 p < 0.05。
只汇报事实，不对结果做解释性包装。

## 产出
results/recall_ti/；results/recall_ti/gate_G3.json

## 验收
7 配置 × 5 seed 齐全；gate_G3.json 生成

## 论文落点
第 3 章主结果表、消融表、变体对比表

=== FILE: docs/plan/cards/S3-pb.md ===
# S3-pb Plan B：插件化到 SimGCL（仅当 G3 不显著）

- 周次：W3 TI-LightGCN 主实验（11/30 周一 – 12/06 周日）
- 线：研究线
- 估时：1.5 天（条件执行）
- 依赖：gate_G3.json

## 提示词

仅当 gate_G3.json 中完整 TI 相对 LightGCN 不显著时执行。
1. models/ti_simgcl.py：在 SimGCL 的传播上使用 build_weighted_adj() 的加权邻接（复用函数，不复制代码），5 个 seed，报告 TI-SimGCL vs SimGCL 的配对检验。
2. 按“用户内评分方差 = 0 / > 0”与“训练时间跨度三分位”分组，输出 TI vs LightGCN 在各组的差值与检验，写入 results/recall_ti/by_group.json。
3. 在 docs/decisions.md 记录：Plan B 已启动，第 3 章论点改为“与对比学习正交、可叠加，并给出适用边界”。

## 产出
models/ti_simgcl.py；results/recall_ti_simgcl/；results/recall_ti/by_group.json

## 验收
TI-SimGCL 5 seed 齐全；分组结果生成

## 论文落点
第 3 章论点调整（见“关口与 Plan B”）

=== FILE: docs/plan/cards/E1.md ===
# E1 产物导出规范与 v0 打通

- 周次：W3 TI-LightGCN 主实验（11/30 周一 – 12/06 周日）
- 线：工程线
- 估时：1 天
- 依赖：S2-a、E0-b

## 提示词

写 export/export_artifacts.py：从一个 RecBole checkpoint 导出 artifacts/{version}/：
user_emb.npy、item_emb.npy、id_map.json（原始 user_id/item_id ↔ 行号）、faiss.index（IndexFlatIP）、manifest.json（data tag、git commit、模型名、checkpoint 路径、data_scope、离线指标从对应 results/ 读取、生成时间）。
用 LightGCN seed 0 导出 v0。修改 serving/ 的召回模块，只从 artifacts/{version}/ 读取，版本号由环境变量 ARTIFACT_VERSION 指定。
写 tests/test_consistency.py（版本号参数化）：随机取 20 个测试用户，原型召回接口返回的 Top-50 与 eval/full_rank.py 用同样屏蔽规则算出的 Top-50 完全一致。这条测试同时验证 ID 映射。

## 产出
export/export_artifacts.py；artifacts/v0/；tests/test_consistency.py

## 验收
test_consistency.py --version v0 通过

## 论文落点
第 5 章功能测试用例之一（“原型列表与离线评估一致”）

=== FILE: docs/plan/cards/T-b.md ===
# T-b 命题 1、2 文字稿与符号表

- 周次：W3 TI-LightGCN 主实验（11/30 周一 – 12/06 周日）
- 线：写作线
- 估时：0.5 天（你写，Claude Code 核对）
- 依赖：S3-a

## 提示词

我在 thesis/src/03_ti_lightgcn.md 写了命题 1、2 的草稿。请：
1. 逐行检查推导，指出跳步或错误，用“> [检查] …”的批注形式写在对应段落下方，不改我的原文；
2. 对照 thesis/src/symbols.md 检查本节符号，列出冲突（λ、λ₂、γ、μ、α、a、η、ρ、τ、T）；
3. 把 tests/test_ti_lightgcn.py 中命题测试的设置与结果整理成要点清单，放 thesis/notes/prop_check.md，供我写附录。

## 产出
批注；thesis/src/symbols.md；thesis/notes/prop_check.md

## 验收
批注逐条处理完，符号冲突清零

## 论文落点
第 3 章理论性质小节；全文符号表

=== FILE: docs/plan/cards/S3-c.md ===
# S3-c 冷启动分层（训练集口径）

- 周次：W4 召回收尾与冻结（12/07 周一 – 12/13 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S3-b

## 提示词

用 eval/strata.py 对 LightGCN、SimGCL、TI-LightGCN（各 5 seed）计算训练集口径 3–4 / 5–9 / 10–29 / ≥30 四层的 R@10、N@10、人数与占比，输出 results/strata/recall.json 与表；守恒校验必须通过。
“完整系统”一列留到 W6 由端到端结果补上，表配置里先占位。

## 产出
results/strata/recall.json

## 验收
守恒校验 |Δ| < 1e-9

## 论文落点
替换 V8 表 5-8、5-9（区间 0–4 改为 3–4，删除“尚未重跑”注释）

=== FILE: docs/plan/cards/S3-d.md ===
# S3-d 跨域：OP、TH 子采样、AJ 子采样

- 周次：W4 召回收尾与冻结（12/07 周一 – 12/13 周日）
- 线：研究线
- 估时：1 天人工 + 约 1.5 GPU 天
- 依赖：S3-b

## 提示词

1. 写 data/subsample.py：TH 随机抽 10 万用户、AJ 抽 5 万用户（数量与 seed 可配置），保留其全部交互后重新做 5-core 与 LOO，复用 data/prepare_data.py 里的函数，不复制逻辑。产出 processed/TH_s100k/、processed/AJ_s50k/，更新 CHECKSUMS，打 tag data-v1-sub；抽样参数写进 docs/口径冻结.md 附录。
2. AJ 的多行为到 α 的映射先读 docs/口径冻结.md；没有定义就停下来问我，不要自行设定。
3. 在 OP、TH_s100k、AJ_s50k 上跑 LightGCN、SimGCL、TI-LightGCN，各 3 个 seed（表注写明），超参沿用 IS 上选定的比例，不在这些数据集的测试集上调参。

## 产出
data/subsample.py；processed/TH_s100k/、AJ_s50k/；results/cross/

## 验收
3 数据集 × 3 模型 × 3 seed 齐全；tag data-v1-sub 存在

## 论文落点
第 3 章跨域表（替换 V8 表 5-5，平均提升列由脚本计算）

=== FILE: docs/plan/cards/S3-e.md ===
# S3-e 敏感性与效率

- 周次：W4 召回收尾与冻结（12/07 周一 – 12/13 周日）
- 线：研究线
- 估时：0.5 天人工 + 约 1 GPU 天
- 依赖：S3-b

## 提示词

在 IS 上做 TI-LightGCN 敏感性，每次只改一个，各 3 个 seed：
λ/λ0 ∈ {0.25, 0.5, 1, 2, 4}；L ∈ {1, 2, 3, 4}；d ∈ {32, 64, 128}；μ ∈ {0, 1e-3, 1e-2, 1e-1}；α_5 : α_4 : α_3 三组比值。
由 scripts/make_figures.py 画 5 张折线图（均值 ± 标准差阴影，样式用 plot_style.py）。
效率表从已有 manifest.json 汇总：每轮耗时、峰值显存、收敛轮数、参数量，覆盖 IS 与 TH_s100k，不另跑。

## 产出
results/sens_ti/；figures/sens/*.svg|png；效率表配置

## 验收
5 张图生成；效率表数字全部来自 manifest

## 论文落点
第 3 章敏感性与效率小节（替换 V8 表 5-13 与“5.8 分钟/轮”）

=== FILE: docs/plan/cards/S3-f.md ===
# S3-f 冻结召回模型，导出候选集

- 周次：W4 召回收尾与冻结（12/07 周一 – 12/13 周日）
- 线：研究线
- 估时：0.5 天
- 依赖：S3-b、S3-e

## 提示词

1. 把 TI-LightGCN 最终配置写进 docs/decisions.md，打 git tag recall-freeze。
2. 用 seed 0 的最终 checkpoint 为全体 IS 用户导出 Top-100 候选（屏蔽训练与验证物品），保存 results/candidates/ti_top100.parquet；另存一份屏蔽训练物品、用于构造排序训练难负例的版本。
3. 记录测试物品被 Top-100 覆盖的比例，写入 results/candidates/coverage.json。
4. 把 rank/ 的候选文件默认路径改为这个文件，重跑 DIN smoke 确认流程无误。

## 产出
results/candidates/；tag recall-freeze

## 验收
coverage.json 生成；DIN smoke 在新候选上正常

## 论文落点
第 4 章实验设置：候选集来源与覆盖率

=== FILE: docs/plan/cards/E2.md ===
# E2 离线流水线一条命令，导出 v1

- 周次：W4 召回收尾与冻结（12/07 周一 – 12/13 周日）
- 线：工程线
- 估时：1.5 天
- 依赖：E1、S3-f

## 提示词

把导出流程串成一条命令：make artifacts V=v1 MODEL=ti_lightgcn CKPT=<路径>
步骤：导出嵌入与 id_map → 建 FAISS IndexFlatIP → 计算 I2I（物品嵌入余弦 Top-50）与类目热门榜 → 写 manifest.json。
manifest 中的离线指标必须从 results/recall_ti/ 读取，不手填。
原型切换到 v1，运行 test_consistency.py --version v1。
另外支持 MODE=demo：用截至最后时间点的全部历史重训一次，供原型演示；manifest 的 data_scope 记录 train_only 或 full_history，二者不能混用于离线评估。

## 产出
Makefile artifacts 目标；artifacts/v1/

## 验收
test_consistency.py --version v1 通过；manifest 指标与结果表一致

## 论文落点
第 5 章离线计算模块的设计与实现；“离线实验仅训练集 / 演示版全量历史”的说明

=== FILE: docs/plan/cards/T-c.md ===
# T-c 重写综述（第 1 章 1.2 与第 2 章）

- 周次：W4 召回收尾与冻结（12/07 周一 – 12/13 周日）
- 线：写作线
- 估时：1.5 天（你写）
- 依赖：L-b

## 提示词

根据 refs/thesis.bib 中已核查的条目，生成 thesis/notes/related_matrix.md：每篇一行，列为 key、年份、会议或期刊、任务（召回/排序/解释）、是否用 LLM、LLM 在线还是离线、是否蒸馏、是否建模时间、是否用图、与本文的关系（留空由我填）。
另外检查我写的 thesis/src/01_intro.md 1.2 节：每个 [@key] 是否在 bib 中，引用处的说法与条目标题是否明显不符（只标出可疑处）。
不要写综述段落。

## 产出
thesis/notes/related_matrix.md；01_intro.md 1.2 节（你写）

## 验收
1.2 节中 KAR、DLLM2Rec、RLMRec、孙浩然 2025 均已讨论区别；无“首次”“填补空白”

## 论文落点
第 1 章国内外研究现状

=== FILE: docs/plan/cards/S4a-a.md ===
# S4a-a vLLM 部署与测速，定预算

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：研究线
- 估时：0.5 天

## 提示词

在单独的 conda 环境 llm 中部署 vLLM，模型 Qwen2.5-7B-Instruct（bf16）。把 HuggingFace 仓库 revision hash、vLLM 版本、max_model_len、gpu_memory_utilization 写入 llm/README.md 与 docs/decisions.md。
写 llm/bench.py：用 1000 条真实格式的 Prompt（取训练集历史构造）分别测 Memory 生成的输出 token/s，以及“是/否”打分的条/秒（开启前缀缓存）。
据此估算全量耗时，写 results/llm/budget.json，并给出两档方案：全量用户 / 抽样 N 万用户做蒸馏（Memory 始终全量）。由我决定。

## 产出
llm/README.md；llm/bench.py；results/llm/budget.json

## 验收
两档方案的耗时估算齐全，决定已写入 decisions.md

## 论文落点
第 4 章实验设置：教师模型、版本、温度、时长

=== FILE: docs/plan/cards/S4a-b.md ===
# S4a-b User Memory 生成与防泄漏

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：研究线
- 估时：1 天 + 夜间批跑
- 依赖：S4a-a

## 提示词

写 llm/build_memory.py：
- 输入只用每个用户的训练集交互（商品标题、类目、评分、时间），按时间排序取最近 M 条（M 写进配置）。Prompt 模板放 llm/prompts/memory_v1.txt，要求输出固定 JSON 字段（关注品类、常见用途、品牌倾向、偏好变化），禁止写入历史中没有的信息。
- 温度 0，批量推理，断点续跑（已完成的 user_id 跳过），输出 artifacts_llm/user_memory.jsonl，每行带 data tag、模型 revision、prompt 版本。
- 用 paraphrase-multilingual-MiniLM-L12-v2 编码为 384 维 memory_emb.npy。
- llm/check_leak.py：断言任何用户的 Prompt 中都不含其验证或测试物品的 ID 与标题；随机抽 50 条生成 results/llm/memory_review.csv（Prompt、输出、空白的人工判断列）供我检查。
全量任务放进 queue.txt 夜间执行，前台不要等待。

## 产出
llm/build_memory.py；llm/prompts/memory_v1.txt；user_memory.jsonl；memory_emb.npy；results/llm/memory_review.csv

## 验收
check_leak 0 命中；覆盖用户数等于计划数；50 条人工检查完成

## 论文落点
第 4 章 User Memory 小节；附录 Prompt；V8 中“256 维”“注册行业”等说法据此改正

=== FILE: docs/plan/cards/S4a-c.md ===
# S4a-c 教师打分与教师质量

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：研究线
- 估时：1 天 + 夜间批跑
- 依赖：S4a-b、S3-f

## 提示词

写 llm/teacher_score.py：
- 对 rank/samples.py 产出的训练样本对 (u, i)，Prompt = 该用户 Memory + 训练历史摘要 + 候选商品标题与类目，要求只回答“是”或“否”；max_tokens=1，用 vLLM 的 logprobs 读取首个生成位置上这两个 token 的对数概率（必要时用 allowed_token_ids 限定为这两个 token），ℓ_T = log p(是) − log p(否)，它等于两者 logit 之差。打分时 temperature 设为 1.0，读到的是模型原始分布的对数概率，生成的那个 token 本身不用。存 teacher_scores.parquet（含 prompt 版本）。
- 先确认分词器中“是”“否”各为单个 token；不是的话换成单 token 的候选词，并写进 decisions.md。
- 质量评估：取验证集 5000 个用户 × 其 TI 候选中 20 个物品（含验证物品）打分，计算教师 AUC、GAUC、ECE，画可靠性图，输出 results/llm/teacher_quality.json 与 figures/llm/。
打分规模按 budget.json 的决定执行，放夜间队列。

## 产出
llm/teacher_score.py；teacher_scores.parquet；results/llm/teacher_quality.json；可靠性图

## 验收
teacher_quality.json 与图生成；打分覆盖的样本数等于计划数

## 论文落点
第 4 章蒸馏小节与教师质量分析（V8 中“输出 0–1 浮点分数”的做法据此替换）

=== FILE: docs/plan/cards/S4b-0.md ===
# S4b-0 排序基线 DIN、DIEN、SASRec、TiSASRec

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：研究线
- 估时：1 天人工 + 约 0.5 GPU 天
- 依赖：S2-c、S3-f

## 提示词

在 rank/ 中加入 DIEN、SASRec、TiSASRec。优先移植作者公开实现，把来源仓库与 commit 记录在 rank/models/THIRD_PARTY.md；样本构造与评估统一用 rank/samples.py 与 rank/eval_rank.py，候选集用 results/candidates/ti_top100.parquet。
DIN、DIEN、SASRec、TiSASRec 各 5 个 seed，按 isolated 协议输出 AUC、GAUC、NDCG@10，结果放 results/rank_base/。
GPU 白天给这批任务；vLLM 任务在 queue.txt 中标注为夜间执行。

## 产出
rank/models/{dien,sasrec,tisasrec}.py；rank/models/THIRD_PARTY.md；results/rank_base/

## 验收
4 模型 × 5 seed 齐全

## 论文落点
第 4 章对比方法与主表（基线行）

=== FILE: docs/plan/cards/E2-b.md ===
# E2-b Memory 进产物目录

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：工程线
- 估时：0.5 天
- 依赖：S4a-b、E2

## 提示词

扩展 make artifacts：可选加入 user_memory.jsonl、memory_emb.npy、item_meta.json（标题、类目、details；price 缺失时为 null 并能被下游正确处理）。
原型的“用户画像”接口改为读取 user_memory.jsonl；没有 Memory 的用户返回明确的空状态，不报错。
导出一个中间版本 v1m 用于联调（不对外宣称，manifest 写明）。

## 产出
artifacts/v1m/；serving 画像接口

## 验收
对有/无 Memory 的两个用户，画像接口分别返回内容与空状态

## 论文落点
第 5 章数据设计：产物清单

=== FILE: docs/plan/cards/O-a.md ===
# O-a 约好 3 名标注者，写评分细则

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：事务
- 估时：0.5 天

## 说明
联系 3 名有工科背景的同学，约定 W7（12/28–01/03）中的 2 小时标注时间，元旦前完成。

## 提示词

根据执行计划 S6-a 的评估设计，起草 docs/rubric.md：维度为准确性、个性化、可读性、决策支撑，每个维度 1–5 分，每一档给出判断标准与一个示例（示例用 IS 中真实商品，不编造型号）。
这是事务性文档，可以由你起草；我会修改后发给标注者。

## 产出
docs/rubric.md；标注者名单与时间（不进仓库）

## 验收
3 人确认时间

## 论文落点
第 5 章解释质量评估的方法描述

=== FILE: docs/plan/cards/T-d.md ===
# T-d 第 3 章方法部分

- 周次：W5 LLM 教师离线部署（12/14 周一 – 12/20 周日）
- 线：写作线
- 估时：1.5 天（你写）
- 依赖：S3-a、T-b

## 提示词

为第 3 章方法部分准备素材，写到 thesis/notes/ch3_facts.md，不写正文：
1. 从 models/ti_lightgcn.py 与最终配置提取每个需要出现在论文里的事实：边权公式、归一化、两种时钟、负反馈处理、长尾正则形式、默认超参、复杂度，每条附代码位置（文件:行号）；
2. 列出 V8 第 4.1 节（thesis/v8_md/ch4.md）中与代码不一致或已经废弃的说法，逐条对照；
3. 我写完 thesis/src/03_ti_lightgcn.md 的方法部分后，对照 symbols.md 检查公式符号，列出冲突。

## 产出
thesis/notes/ch3_facts.md；03_ti_lightgcn.md 方法部分（你写）

## 验收
方法部分每个公式为 LaTeX，符号与 symbols.md 一致

## 论文落点
第 3 章 3.1–3.4

=== FILE: docs/plan/cards/S4b-a.md ===
# S4b-a Temporal-DIN 与统一蒸馏损失

- 周次：W6 排序、端到端与 v2（12/21 周一 – 12/27 周日）
- 线：研究线
- 估时：1 天
- 依赖：S4a-c、S4b-0

## 提示词

在 rank/models/temporal_din.py 实现：
- 注意力：ã_k = softmax_k( a(e_k, e_c) − γ · g(Δt_k) )，g 支持 linear（Δt/Δ_day）与 log（ln(1 + Δt/Δ_day)）；γ 初值取 results/profile/IS.json 的 γ0，可选 learnable（softplus 参数化）。
- 短期通道：最近 N 条行为（N 可配）；长期通道：memory_emb（384 维，经线性层投影）；门控融合；MLP 结构从配置读取，论文按配置写。
- 损失：(1 − η)·BCE(y, σ(ℓ_S)) + η·τ²·ω·BCE(σ(ℓ_T/τ), σ(ℓ_S/τ))，ω = |2p_T − 1|^κ，κ = 0 时不加权。
测试 tests/test_temporal_din.py：
 (1) 两步写法（softmax 后乘衰减再归一化）与合成写法数值相等；
 (2) 所有 Δt 同加一个常数，注意力权重不变；
 (3) γ = 0 且去掉长期通道时，加载同一组权重后与 rank/models/din.py 的输出逐元素相等。

## 产出
rank/models/temporal_din.py；rank/losses.py；tests/test_temporal_din.py

## 验收
三项测试通过

## 论文落点
第 4 章模型与蒸馏目标（替换 V8 式 4-8、4-9、4-14 至 4-16）

=== FILE: docs/plan/cards/S4b-b.md ===
# S4b-b 排序主实验、消融、敏感性

- 周次：W6 排序、端到端与 v2（12/21 周一 – 12/27 周日）
- 线：研究线
- 估时：1 天人工 + 约 1 GPU 天
- 依赖：S4b-a

## 提示词

isolated 协议，5 个 seed：Temporal-DIN；+User Memory（特征增强，不蒸馏）；+蒸馏（完整）。
消融（5 seed）：去时间偏置、去 Memory、去门控（改为拼接）、去蒸馏。表中“去 Memory 与蒸馏”一行如仍保留时间偏置，标签写成“Temporal-DIN（无 Memory、无蒸馏）”，不要叫“标准 DIN”。
敏感性（3 seed）：η ∈ {0, 0.1, 0.3, 0.5, 1.0}、τ ∈ {1, 2, 4}、N ∈ {5, 10, 20}、g ∈ {linear, log}、κ ∈ {0, 1}。
结果放 results/rank_main/、rank_ablation/、rank_sens/；完整模型 vs DIN、完整 vs 无蒸馏的按用户配对检验写入 results/rank_main/gate_G6.json。

## 产出
results/rank_main/；rank_ablation/；rank_sens/；gate_G6.json

## 验收
主表与消融 5 seed 齐全；gate_G6.json 生成

## 论文落点
第 4 章主结果、消融、敏感性（替换 V8 表 5-6、5-12、5-14）

=== FILE: docs/plan/cards/E3.md ===
# E3 原型接入 v2 并冻结

- 周次：W6 排序、端到端与 v2（12/21 周一 – 12/27 周日）
- 线：工程线
- 估时：1.5 天
- 依赖：E2-b、S4b-b

## 提示词

1. make artifacts V=v2：在 v1m 基础上加入 din.pt、din_vocab.json，manifest 记录排序模型的离线指标（从 results/rank_main/ 读）。
2. serving/pipeline.py 提供 recommend(user_id, artifacts, options)：多路召回（图、语义、I2I、热门）→ RRF 融合（k = 60，各路权重从 configs/serving.yaml 读取，取值在验证集上选）→ Temporal-DIN 精排 → 语义重排（列表内 z-score 后按 ρ 加权）→ Top-20，并标注每条的召回来源。API 层只调用这个函数。
3. 降级：任一路索引缺失、用户没有 Memory 时的处理，日志记录降级模式。
4. 写好 tests/test_consistency_v2.py：对 20 个测试用户，API 返回的 Top-10 与 run_e2e.py 中“完整系统”行的逐用户列表一致。这条测试在 S5 产出 results/e2e/ 之后运行。
一致性测试通过后打 tag artifacts-v2，之后的系统测试只用 v2。

## 产出
serving/pipeline.py；configs/serving.yaml；artifacts/v2/；tag artifacts-v2

## 验收
API 对 20 个测试用户返回结果；降级用例手动验证一次；S5 完成后 test_consistency_v2 通过

## 论文落点
第 5 章在线服务设计、时序图、接口说明；RRF 公式（替换 V8 的 0.4/0.3/0.2/0.1）

=== FILE: docs/plan/cards/S5.md ===
# S5 端到端评估（不补入测试物品）

- 周次：W6 排序、端到端与 v2（12/21 周一 – 12/27 周日）
- 线：研究线
- 估时：1 天
- 依赖：S4b-b、E3

## 提示词

写 experiments/run_e2e.py：对每个测试用户，召回 Top-100（不补入测试物品）→ 排序模型打分 → 取 Top-10，计算 R@10、N@10，输出 per_user.parquet。
组合：BPR-MF+DIN、LightGCN+DIN、SimGCL+DIEN、TI+DIN、LightGCN+Temporal-DIN（完整）、TI+Temporal-DIN（完整）。
另加“完整系统”一行：直接调用 serving/pipeline.py 的 recommend()（多路召回 + RRF + Temporal-DIN + 语义重排），使用 train_only 产物 v2，保证离线评估和原型走同一段代码。
日志打印每个组合的“召回覆盖率”与“排序后 Top-10 命中率”；断言完整系统的指标由最终列表计算。
用 eval/strata.py 为完整系统补齐冷启动分层那一列。

## 产出
experiments/run_e2e.py；results/e2e/；results/strata/e2e.json

## 验收
完整系统的 R@10 来自最终列表；分层守恒通过

## 论文落点
替换 V8 表 5-7；冷启动分层表的“完整系统”列

=== FILE: docs/plan/cards/T-e.md ===
# T-e 第 4 章方法部分

- 周次：W6 排序、端到端与 v2（12/21 周一 – 12/27 周日）
- 线：写作线
- 估时：1 天（你写）
- 依赖：S4b-a

## 提示词

为第 4 章方法部分准备素材，写到 thesis/notes/ch4_facts.md，不写正文：
1. 从 rank/models/temporal_din.py、rank/losses.py、llm/ 与最终配置提取事实：注意力合成形式、γ 的取值方式、短期通道 N、Memory 维度（384）与投影、门控、MLP 结构、损失形式与 η、τ、κ 取值、教师模型与版本，每条附代码位置；
2. 列出 V8 第 4.2、4.3 节中与代码不一致的说法（如 7 天窗口、γ=0.3、256 维、MSE 蒸馏、Qwen API、注册行业），逐条对照；
3. 列出与 KAR、DLLM2Rec 的差异点，供我写“与相关工作的区别”。

## 产出
thesis/notes/ch4_facts.md；04_temporal_din.md 方法部分（你写）

## 验收
方法部分无 V8 遗留的不一致说法

## 论文落点
第 4 章 4.1–4.4

=== FILE: docs/plan/cards/S6-a.md ===
# S6-a 解释质量：自动、LLM 评审、人工

- 周次：W7 解释评估与系统测试（12/28 周一 – 01/03 周日（含元旦，按 4 个工作日排））
- 线：研究线
- 估时：1 天 + 标注者 2 小时
- 依赖：E4、O-a

## 提示词

1. 从测试集按固定 seed 抽 100 个（用户，推荐商品）对，推荐商品取 v2 系统 Top-10 中的一个；生成三种解释：无 RAG、RAG、模板。
2. eval/explain_attr.py：从解释中抽取品牌、材质、尺寸、数值参数，与 item_meta 的 details 比对，计算属性一致率；涉及价格的句子单独统计（IS 价格字段覆盖率只有 74.7%）。
3. eval/llm_judge.py：用与生成模型不同的模型，按 docs/rubric.md 打分，记录模型名与版本。
4. 生成 annotate/index.html：单文件离线标注页，三种解释随机顺序、隐藏来源，结果导出 CSV。我发给 3 名标注者。
5. 收回 CSV 后计算各维度均值、Fleiss κ、LLM 评审与人工评分的 Spearman 相关，输出 results/explain/。BLEU/ROUGE 只作辅助列。

## 产出
eval/explain_attr.py；eval/llm_judge.py；annotate/index.html；results/explain/

## 验收
属性一致率、LLM 评审、人工均值与 κ 都已输出

## 论文落点
第 5 章解释质量评估（替换 V8 5.9 的“5 位专家”与表 5-15、5-16）

=== FILE: docs/plan/cards/S6-b.md ===
# S6-b 真实用户案例（脚本可复现）

- 周次：W7 解释评估与系统测试（12/28 周一 – 01/03 周日（含元旦，按 4 个工作日排））
- 线：研究线
- 估时：0.5 天
- 依赖：S5

## 提示词

写 scripts/case.py --user_id X：输出该用户训练历史（匿名 ID + 真实商品标题 + 日期）、Memory、Temporal-DIN 对历史各条的注意力权重（程序实际值）、基线与本文的 Top-10、测试物品排名、解释文本，生成 Markdown 与注意力热力图。
按规则选 3 个成功案例（本文命中而 LightGCN+DIN 未命中）和 2 个失败案例，选取规则写在脚本里（固定 seed 随机抽），不手挑。
同一 user_id 运行两次输出必须一致。

## 产出
scripts/case.py；results/cases/；figures/cases/

## 验收
5 个案例可复现

## 论文落点
第 4 章真实案例（替换 V8 5.10 中的西门子、倍福、OMRON 虚构序列）

=== FILE: docs/plan/cards/E4.md ===
# E4 RAG 解释接入原型

- 周次：W7 解释评估与系统测试（12/28 周一 – 01/03 周日（含元旦，按 4 个工作日排））
- 线：工程线
- 估时：1 天
- 依赖：E3

## 提示词

在 serving/explain/ 实现：item_meta 建向量库（Chroma 或 FAISS 二选一，以论文写的为准，不一致就改论文），解释生成可以调用 API，加缓存；缓存未命中时接口先返回占位，后台生成完成后写缓存。记录所用模型名与版本到 manifest。
语义编码统一为 384 维（paraphrase-multilingual-MiniLM-L12-v2），不要出现 768 维。

## 产出
serving/explain/；解释接口

## 验收
缓存命中/未命中两条路径手动各验证一次

## 论文落点
第 5 章推荐解释模块

=== FILE: docs/plan/cards/E5.md ===
# E5 功能用例、压测、内存、截图

- 周次：W7 解释评估与系统测试（12/28 周一 – 01/03 周日（含元旦，按 4 个工作日排））
- 线：工程线
- 估时：1.5 天
- 依赖：E3、E4

## 说明
界面截图 5–8 张由你手动完成，用 IS 中的真实商品，放 figures/screens/。

## 提示词

1. 先起草 docs/test_cases.md（15–25 条：首页推荐、过滤已购、召回来源标注、解释占位与回填、降级、无 Memory 用户、非法参数、离线一致性……），我确认后在 tests/functional/ 实现，pytest 输出 junit 报告。
2. tests/locustfile.py：缓存命中、未命中、混合（70% 命中）三个场景，50 并发，各 5 分钟，导出 P50/P95/P99 与 QPS；同时用 psutil 每秒记录服务进程 RSS。机器配置（CPU 型号、核数、内存、是否容器、是否有 GPU）自动写入 results/systest/env.json。
3. 结果写 results/systest/，make_tables 生成功能测试表与性能表。全文所有延迟与内存数字只能引用这里。

## 产出
docs/test_cases.md；tests/functional/；tests/locustfile.py；results/systest/；figures/screens/

## 验收
用例全部通过；三个压测场景结果与 RSS 曲线齐全

## 论文落点
第 5 章测试小节（替换 V8 表 6-2、“130MB”“2 核 2GB”“P99 68ms”等）

=== FILE: docs/plan/cards/T-f.md ===
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

=== FILE: docs/plan/cards/O-b.md ===
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

=== FILE: docs/plan/cards/T-g.md ===
# T-g 第 3、4 章的表、图与数字 key

- 周次：W8 冻结实验，算法章成稿（01/04 周一 – 01/10 周日）
- 线：写作线
- 估时：0.5 天
- 依赖：O-b

## 提示词

为 thesis/src/03_ti_lightgcn.md 与 04_temporal_din.md 的实验小节：
1. 按 configs/tables.yaml 放好全部 {{table:…}} 占位；把正文写分析时可能用到的 numbers.json key 列到 thesis/notes/keys_ch3.md、keys_ch4.md（key、含义、当前值）。
2. 用 make_figures.py 重绘全部实验图（plot_style.py 统一字体字号，SVG + 600dpi PNG）。
3. 运行 check_thesis.py，输出未解析占位符、裸数字、禁用词、图表编号连续性报告。
不要替我写结果分析段落。

## 产出
表格占位；keys_ch3.md、keys_ch4.md；重绘后的 figures/

## 验收
make thesis 对第 3、4 章无未解析占位符

## 论文落点
第 3、4 章实验小节

=== FILE: docs/plan/cards/T-h.md ===
# T-h 第 3、4 章成稿

- 周次：W8 冻结实验，算法章成稿（01/04 周一 – 01/10 周日）
- 线：写作线
- 估时：3 天（你写）
- 依赖：T-g

## 提示词

我写完第 3、4 章后，先运行 /thesis-check，再做一次评审式阅读，输出到 docs/weekly/review_ch34.md，不改正文：
逐节列出：结论是否有对应的表、图或检验支撑；有没有比数据更强的说法；与 KAR、DLLM2Rec 的区别是否写清；V8 中被删掉的无支撑说法是否又出现了。

## 产出
03、04 两章完整稿；review_ch34.md

## 验收
review 清单逐条处理

## 论文落点
第 3、4 章

=== FILE: docs/plan/cards/T-i.md ===
# T-i 第 1、2 章

- 周次：W9 V9 全文初稿（01/11 周一 – 01/17 周日）
- 线：写作线
- 估时：2 天（你写）
- 依赖：T-c

## 提示词

1. 第 2 章压缩：标出 thesis/v8_md/ch2.md 中与本文方法无关、可以删除或压缩的段落（如注意力机制演进史、知识蒸馏与迁移学习关系、综合对比大表），估算删后页数，目标 12–15 页。只给清单。
2. 第 1 章：检查 1.1 中的统计数字是否都有可核查的出处（没有就标出）；1.3 研究内容与创新点是否与第 3–5 章实际做的一致，列出不一致处。

## 产出
01_intro.md、02_background.md（你写）；压缩清单

## 验收
第 2 章 12–15 页；1.1 无无出处数字

## 论文落点
第 1、2 章

=== FILE: docs/plan/cards/T-j.md ===
# T-j 第 5 章测试节与第 6 章

- 周次：W9 V9 全文初稿（01/11 周一 – 01/17 周日）
- 线：写作线
- 估时：1 天（你写）
- 依赖：E5、S6-a

## 提示词

为第 5 章测试小节放好 {{table:systest_*}} 与 {{table:explain_*}} 占位，并列出可引用的 key。
第 6 章“研究不足”需要的事实清单：缺少 B2B 询价与审批日志、无线上 A/B、LLM 预训练语料可能包含 Amazon 评论、TH/AJ 为子采样等，每条附对应的口径文件或决策记录位置。

## 产出
05_system.md 测试节；06_conclusion.md（你写）

## 验收
测试节所有数字来自 results/systest/ 与 results/explain/

## 论文落点
第 5 章 5.5–5.6，第 6 章

=== FILE: docs/plan/cards/T-k.md ===
# T-k 摘要与附录

- 周次：W9 V9 全文初稿（01/11 周一 – 01/17 周日）
- 线：写作线
- 估时：1 天
- 依赖：T-h、T-i、T-j

## 提示词

1. 附录由你生成：从 configs/ 生成超参数表；从 experiments/ 生成复现命令清单（每张表一条命令）；从 llm/prompts/ 收录 Prompt 模板；从 thesis/notes/prop_check.md 整理命题数值验证（要点我已写成段落）。写入 90_appendix.md。
2. 中英文摘要由我写。写完后检查：摘要里每个数字都用占位符、与正文一致；英文摘要只做语法与术语检查，以批注形式给出，不重写句子。

## 产出
90_appendix.md；00_front.md 中的摘要（你写）

## 验收
附录表格全部由脚本生成

## 论文落点
摘要、附录

=== FILE: docs/plan/cards/T-l.md ===
# T-l 构建 V9 与引用检查

- 周次：W9 V9 全文初稿（01/11 周一 – 01/17 周日）
- 线：写作线
- 估时：0.5 天
- 依赖：T-k

## 提示词

运行 make thesis 生成 build/thesis_V9.docx，然后运行 scripts/check_refs.py（没有就先写）：
- 正文引用的每个 key 都在 bib 中，且条目有 DOI 或 URL；
- bib 中没有未被引用的条目；
- citeproc 输出的编号按首次出现顺序单调递增；
- refs/verify.csv 中结论为“删除”的条目没有被引用。
再对全文运行 /thesis-check，汇总成一份清单交给我。

## 产出
build/thesis_V9.docx；引用检查报告

## 验收
引用检查 0 问题

## 论文落点
参考文献表

=== FILE: docs/plan/cards/T-m.md ===
# T-m 审校版逐表核对数字

- 周次：W10 审校与送审稿（01/18 周一 – 01/24 周日）
- 线：写作线
- 估时：1.5 天（你核对）

## 提示词

运行 make thesis AUDIT=1 生成 build/thesis_V9_audit.docx（每个数字后带来源文件）。
另外生成 docs/weekly/number_audit.md：按表列出每个单元格的 key、值、来源文件、manifest 中的 commit 与 data tag；commit 不在 exp-freeze 之前或 data tag 不是 data-v1/data-v1-sub 的，标出来。

## 产出
thesis_V9_audit.docx；number_audit.md

## 验收
你逐表核对完毕，number_audit.md 中无标记项或已说明

## 论文落点
全文

=== FILE: docs/plan/cards/T-n.md ===
# T-n 套学校模板：封面、目录、题注与交叉引用

- 周次：W10 审校与送审稿（01/18 周一 – 01/24 周日）
- 线：写作线
- 估时：1 天（你在 Word 中操作）

## 说明
把 V9 正文合入学校模板（封面、声明、摘要页来自模板）。目录用 Word 自动目录；公式编号按章（3-1）右对齐；图题表题按学院要求处理：要求使用题注域时，用“插入题注”逐个替换（约半天）。最后整篇更新域并另存 PDF 检查一遍页码与目录。

## 产出
thesis_V9_送审稿.docx 与 PDF

## 验收
目录、页码、公式编号、图表编号在 PDF 中全部正确

## 论文落点
全文版式

=== FILE: docs/plan/cards/T-o.md ===
# T-o 盲审匿名检查

- 周次：W10 审校与送审稿（01/18 周一 – 01/24 周日）
- 线：写作线
- 估时：0.5 小时

## 提示词

在 build/ 下的送审稿（先用 pandoc 或 extract 工具转文本）中搜索：IP 地址、本机路径（/root、/Users、C:\）、GitHub 用户名或仓库地址、邮箱、导师与实验室名称、我的姓名与学号，以及“尚未重跑”“仅用于说明趋势”“3.x 节”这类遗留文字，列出所有命中的位置。只报告。

## 产出
docs/weekly/anonymity.md

## 验收
0 命中

## 论文落点
盲审版

=== FILE: docs/plan/cards/T-p.md ===
# T-p 查重与 AIGC 自检

- 周次：W10 审校与送审稿（01/18 周一 – 01/24 周日）
- 线：事务
- 估时：1 天

## 说明
在学院指定或认可的平台各做一次自检；高于阈值的段落用自己的话重写（短句、具体做法与数字、少评价），然后复检。按学校要求填写 AI 工具使用说明（参考 docs/ai_usage.md 的记录）。

## 提示词

我把检测报告中标红的段落粘贴到 docs/detect/flagged.md。请逐段定位到 thesis/src/ 中的文件与行号，按章节列成表（位置、标红类型、段落前 20 字），不改写任何句子。改写由我完成。

## 产出
检测报告；docs/detect/flagged.md 定位表

## 验收
低于学院阈值

## 论文落点
全文

=== FILE: docs/plan/cards/T-q.md ===
# T-q 送审前自查清单

- 周次：W10 审校与送审稿（01/18 周一 – 01/24 周日）
- 线：写作线
- 估时：0.5 天

## 提示词

生成 docs/weekly/final_checklist.md：把执行计划“送审前自查”的 22 项逐项列出，每项填写证据（脚本输出路径或报告文件）或“人工确认：姓名、日期”。能用脚本验证的项现在重新跑一遍再填。

## 产出
docs/weekly/final_checklist.md

## 验收
22 项全部有证据

## 论文落点
送审

=== FILE: docs/plan/cards/O-c.md ===
# O-c 导师意见跟踪

- 周次：W11–12 缓冲：导师意见与定稿（01/25 周一 – 02/05 周五（春节 02/06 前定稿））
- 线：事务
- 估时：按意见量

## 提示词

我把导师批注整理在 docs/advisor/V9_comments.md（每条：位置、意见）。
为每条意见在 docs/advisor/tracker.md 建一行：位置 | 意见 | 类别（数字/表述/结构/格式/实验）| 需要的动作 | 状态。
类别为“实验”的，先判断能否只用已有 results/ 补表；需要新跑的标出来并估算 GPU 时间，由我决定。

## 产出
docs/advisor/tracker.md

## 验收
每条意见都有状态

## 论文落点
全文
