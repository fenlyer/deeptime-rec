# 项目：工业品推荐硕士论文（deeptime-rec）

本仓库同时承载论文实验、原型系统和论文源文件。
执行计划：docs/plan/（任务卡 cards/、关口 gates.md）。当前进度：@docs/STATUS.md
口径：@docs/预处理口径冻结.md  决策记录：docs/decisions.md

## 红线
1. 不修改 data/processed/、data/CHECKSUMS.sha256、docs/预处理口径冻结.md。数据或口径需要变化时停下来问我，由我决定并记入 docs/decisions.md。
2. 论文中的实验数字只能来自 thesis/generated/numbers.json（由 scripts/make_tables.py 从 results/ 生成），正文用 {{n:key}} 引用。不手写、不估计、不取整美化任何结果数字。
3. 不为改善指标修改 eval/、configs/eval.yaml、切分或屏蔽规则。评估代码的任何改动先说明原因，等我确认。
4. 验证集只用于早停与选参；测试集只在最终评估读取。不在测试集上调参，不挑 seed。
5. 不生成、不补全参考文献条目（作者、标题、DOI、页码）。refs/thesis.bib 只由我从 Zotero 导出。
6. 论述、分析、结论段落由我执笔。你负责列事实清单、核对数字与代码一致性、指出问题、做结构与格式修改。我明确说"起草"时，草稿写到 thesis/drafts/，不直接写入 thesis/src/。
7. 结果异常时先列出可能原因和验证办法，不要直接改代码去"修好"结果。

## 运行规范
- 每次训练或评估都经 common/run.py 记录到 results/{exp}/{model}/seed{n}/：metrics.json、per_user.parquet、config.yaml、train_log.csv、manifest.json。
- 工作区有未提交改动时不启动正式实验；smoke 实验放 results/_smoke/。
- 预计超过 10 分钟的任务：写成脚本，追加到 experiments/queue.txt，由 queue.sh 在 tmux 后台执行；告诉我日志路径，不在会话里等待。
- 只用训练集建图、训练、生成 User Memory。原型演示版例外，manifest 中 data_scope 必须写 full_history。
- seed 取 0–4；主结果 5 个 seed，敏感性与跨域 3 个 seed。

## 代码规范
- 先写或更新测试，再实现；pytest 全过才算完成。评估、边权、注意力、损失函数必须有数值测试。
- 边权构造、ID 映射、样本构造各只有一个实现，其他地方复用，不复制。
- commit message 以任务卡 ID 开头，例如 "S1-a: 统一全排序评估"。
- 改动 eval/、data/、configs/eval.yaml 时，在回复开头单独提醒我。

## 常用命令
make test                    # 全部测试
make gate W=3                # 第 3 周关口检查（python -m gates.w3）
make tables                  # results/ → thesis/generated/
make thesis [AUDIT=1]        # 生成 build/thesis_V9.docx（AUDIT=1 时数字后附来源）
make artifacts V=v1 ...      # 导出原型产物

## 环境（按实际修改）
- GPU：AutoDL RTX 4090 24GB，16 vCPU / 60 GB；数据盘 /root/autodl-tmp 50G
- AutoDL conda 环境：rec（RecBole）、llm（vLLM）、serve（原型，uv 锁定）
- 本机 conda 环境：`recbole_env`（Python 3.10.18 / recbole 1.2.1 / torch 2.5.1）对应 AutoDL 的 `rec`；`base`（Python 3.12.2）跑 CPU 侧脚本
- 解释器约定：`make` 里的 `PY` 默认 `python3`，取决于 PATH（`backend/.venv` 可能抢先）。跑研究侧任务前用 `make check-env` 确认，或显式指定 `PY=/opt/anaconda3/bin/python3`
- 依赖锁定：研究侧 CPU 环境见 `environment/research.yml`，RecBole 侧见 `environment/recbole.yml`

## 符号约定（论文与代码一致）
λ 图时间衰减率；λ₂ L2 正则；μ 长尾正则强度；α_r 反馈强度；a_k 注意力权重；
γ 注意力时间衰减率；η 蒸馏损失权重；ρ 语义重排权重；τ 蒸馏温度；时间单位为天（Δ_day = 86400 s）。

## 论文源 thesis/src/
- Markdown 正文；公式用 LaTeX（$…$ / $$…$$）；引用 [@key]；数字 {{n:key}}；表格 {{table:name}}。
- 禁用词：首次、填补空白、创造性地、范式性突破、彻底解决、值得注意的是、充分体现了。

## 目录
data/ 冻结数据与预处理 common/ 运行记录 eval/ 统一评估与统计 configs/ 全部配置
models/ 召回模型 rank/ 排序模型与样本 llm/ 教师与 Memory experiments/ 复现脚本与队列
results/ 结果 gates/ 每周关口检查 export/ 产物导出 artifacts/ 原型产物 serving/ 原型后端 tests/ 测试
scripts/ 表、图、论文构建与检查 refs/ 文献 thesis/ 论文源 docs/ 计划、决策、周报
backend/ 现有原型后端（FastAPI） frontend/ 现有原型前端（React） environment/ 环境锁定
figures/ 论文实验图 build/ 论文构建产物 annotate/ 标注页 artifacts_llm/ LLM 中间产物 artifacts_static/ 模型静态输入
