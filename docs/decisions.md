# 决策记录
格式：日期｜决定｜理由｜影响的文件或章节｜是否要改论文

- 2026-11-15｜采用执行计划 V1（W1 = 2026-11-16）｜—｜全部｜—
- 2026-11-16｜CLAUDE.md 中的口径文件引用统一为 `docs/预处理口径冻结.md`（原写作 `docs/口径冻结.md`，与实际文件名不符）｜执行计划按简称书写，仓库内实际文件带「预处理」前缀，保持引用可点击｜CLAUDE.md 红线 1 与首部、docs/plan/gates.md G2 条件、cards E0-a/S2-b/S3-d｜否
- 2026-11-16｜删除 `docs/todolist.txt`，待办与进度统一记入执行计划：任务卡 docs/plan/cards/、关口 docs/plan/gates.md、当前进度 docs/STATUS.md｜todolist 与执行计划职责重复，内容已过时（最近一条只到 2026-11-13）｜docs/预处理口径冻结.md 第七节第 6 步改为写入 docs/decisions.md｜否
- 2026-11-16｜`data/` 下脚本不改动位置（prepare_data.py 与三个 verify_*.py 原地保留）｜data/README.md 的「论文章节→脚本→产物」映射表与 S0-a 卡片均按 `python data/verify_*.py` 书写，移动会造成引用断裂｜CLAUDE.md 目录一节、data/README.md｜否
- 2026-11-16｜W0-a 补充建立执行计划引用的工作目录：docs/weekly、docs/advisor、docs/detect、figures、environment、build、annotate、artifacts_llm、artifacts_static、thesis/{src,notes,drafts,generated/tables,v8_md,template,figures_src}、rank/models、llm/prompts、serving/explain、tests/{functional,fixtures}、configs/{recall,rank}｜避免卡片执行时因目录不存在而中断；CLAUDE.md 目录一节同步补入｜CLAUDE.md「目录」一节、.gitignore、Makefile｜否
- 2026-11-17｜引入 RecBole 作为召回基线训练器（BPR-MF / NGCF / LightGCN / SGL 用 RecBole，SimGCL 用 RecBole-GNN）｜官方实现可核对、避免自写基线引入偏弱 bug、答辩时无"压低基线"质疑；数据经 adapter 从 processed/ 导出为预切分 atomic 文件，通过 benchmark_filename 加载，RecBole 内部过滤全部关闭；eval/、configs/eval.yaml、切分与屏蔽规则不变，满足红线第 3 条；TI-LightGCN 保留 PyG 自研，不进入 RecBole｜docs/plan/cards/S1-b、S2-a、S3-a；scripts/export_recbole.py（新增）；configs/recbole_baselines.yaml（新增）；tests/verify_recbole_adapter.py（新增）｜是（第 3 章实验设置、表 5-2 软件环境补 RecBole / RecBole-GNN 版本）
- 2026-11-17｜W0-b 三样外部信息已确认：① 送审截止日不卡，2027-06 前答辩（系统已盲审过）；② 查重平台 CNKI TMLC2/VIP，全文及单章 ≤ 10% 或 15%，AIGC 疑似率 ≤ 10%（严控线）；③ 学校模板已放入 thesis/template/｜—｜docs/plan/gates.md G10、thesis/template/｜否
- 2026-11-17｜W0-c AutoDL 环境已选定（RTX 4090 24GB / 16 vCPU / 60 GB / 数据盘 50G），当前无余额，待晚间确认释放实例｜CLAUDE.md 环境一节已更新｜—｜否
- 2026-11-17｜备份目标定为本地目录 `~/deeptime-rec-backup`，可用环境变量 `BACKUP_DEST` 覆盖；备份范围：results/ 下所有 metrics.json 与 manifest.json、artifacts/*/manifest.json、thesis/、refs/、docs/｜W0-c 卡片要求由我指定备份位置；本地目录无需网络、可随时执行｜scripts/backup.sh、Makefile backup 目标｜否
- 2026-11-17｜实验队列 experiments/queue.sh 采用 `--foreground` / `--dry-run` / `--status` 三种模式；tmux 模式在本机不可用（未安装 tmux），AutoDL 上可用｜macOS 自带 bash 3.2 无 mapfile，脚本已改写为 while read 兼容写法｜experiments/queue.sh、experiments/queue.txt｜否