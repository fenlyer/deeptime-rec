# 决策记录
格式：日期｜决定｜理由｜影响的文件或章节｜是否要改论文

- 2026-11-15｜采用执行计划 V1（W1 = 2026-11-16）｜—｜全部｜—
- 2026-11-16｜CLAUDE.md 中的口径文件引用统一为 `docs/预处理口径冻结.md`（原写作 `docs/口径冻结.md`，与实际文件名不符）｜执行计划按简称书写，仓库内实际文件带「预处理」前缀，保持引用可点击｜CLAUDE.md 红线 1 与首部、docs/plan/gates.md G2 条件、cards E0-a/S2-b/S3-d｜否
- 2026-11-16｜删除 `docs/todolist.txt`，待办与进度统一记入执行计划：任务卡 docs/plan/cards/、关口 docs/plan/gates.md、当前进度 docs/STATUS.md｜todolist 与执行计划职责重复，内容已过时（最近一条只到 2026-11-13）｜docs/预处理口径冻结.md 第七节第 6 步改为写入 docs/decisions.md｜否
- 2026-11-16｜`data/` 下脚本不改动位置（prepare_data.py 与三个 verify_*.py 原地保留）｜data/README.md 的「论文章节→脚本→产物」映射表与 S0-a 卡片均按 `python data/verify_*.py` 书写，移动会造成引用断裂｜CLAUDE.md 目录一节、data/README.md｜否
- 2026-11-16｜W0-a 补充建立执行计划引用的工作目录：docs/weekly、docs/advisor、docs/detect、figures、environment、build、annotate、artifacts_llm、artifacts_static、thesis/{src,notes,drafts,generated/tables,v8_md,template,figures_src}、rank/models、llm/prompts、serving/explain、tests/{functional,fixtures}、configs/{recall,rank}｜避免卡片执行时因目录不存在而中断；CLAUDE.md 目录一节同步补入｜CLAUDE.md「目录」一节、.gitignore、Makefile｜否