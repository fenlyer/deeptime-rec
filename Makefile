# Makefile — 论文工程统一入口
#
# 本文件只是骨架：每个目标在对应任务卡实现脚本后才会真正生效。
# 目标未实现时以非零码退出，避免误判为通过。

SHELL := /bin/bash
PY    := python3

.PHONY: help test gate tables thesis smoke artifacts backup

help:
	@echo "make test                  全部测试                      (S1-a,S1-c,S1-d)"
	@echo "make gate W=3              第 N 周关口检查               (.claude/commands/gate.md)"
	@echo "make tables                results/ → thesis/generated/ (S1-d)"
	@echo "make thesis [AUDIT=1]      生成 build/thesis_V9.docx    (T-a,T-l)"
	@echo "make smoke                 pandoc 冒烟文档               (T-a)"
	@echo "make artifacts V=v1 ...    导出原型产物                  (E1,E2,E3)"
	@echo "make backup                备份结果与论文源              (W0-c)"

test:
	@ls tests/**/test_*.py tests/test_*.py >/dev/null 2>&1 || { echo "tests/ 尚无测试文件，见 docs/plan/cards/S1-a.md"; exit 1; }
	$(PY) -m pytest tests/ -q

gate:
	@test -n "$(W)" || { echo "用法：make gate W=3（对应 docs/plan/gates.md 的 G3）"; exit 1; }
	@test -f gates/w$(W).py || { echo "gates/w$(W).py 尚未实现，按 docs/plan/gates.md 的 G$(W) 条件编写"; exit 1; }
	$(PY) -m gates.w$(W)

tables:
	@test -f scripts/make_tables.py || { echo "scripts/make_tables.py 尚未实现，见 docs/plan/cards/S1-d.md"; exit 1; }
	$(PY) scripts/make_tables.py

thesis:
	@test -f scripts/build_thesis.py || { echo "scripts/build_thesis.py 尚未实现，见 docs/plan/cards/S1-d.md 与 T-a.md"; exit 1; }
	$(PY) scripts/build_thesis.py $(if $(AUDIT),--audit,)

smoke:
	@test -f thesis/smoke.md || { echo "thesis/smoke.md 尚未创建，见 docs/plan/cards/T-a.md"; exit 1; }
	@test -f thesis/reference.docx || { echo "thesis/reference.docx 尚未创建，见 docs/plan/cards/T-a.md（需 W0-b 的学校模板）"; exit 1; }
	pandoc thesis/smoke.md -o build/smoke.docx --reference-doc=thesis/reference.docx

artifacts:
	@test -n "$(V)" || { echo "用法：make artifacts V=v1 MODEL=ti_lightgcn CKPT=<路径>"; exit 1; }
	@test -f export/export_artifacts.py || { echo "export/export_artifacts.py 尚未实现，见 docs/plan/cards/E1.md"; exit 1; }
	$(PY) export/export_artifacts.py --version $(V) \
		$(if $(MODEL),--model $(MODEL),) $(if $(CKPT),--ckpt $(CKPT),) $(if $(MODE),--mode $(MODE),)

backup:
	@test -f scripts/backup.sh || { echo "scripts/backup.sh 尚未实现，见 docs/plan/cards/W0-c.md"; exit 1; }
	bash scripts/backup.sh
