# T-build 论文构建与冒烟测试

- 周次：W5（01/04 – 01/08）
- 线：研究线（工具链）
- 估时：1 天
- 依赖：S1-d（numbers.json）、T-ch3/T-ch4/T-ch5（正文 Markdown）
- 阻塞：论文最终 .docx 生成

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ❌ 不需要 |
| **SSH** | 不需要（本机运行） |
| **时长** | ≈ 4 小时 |

## 为什么必须有这张卡

V9 计划切换（commit 02af8b9）时删除了旧卡 T-a ~ T-q（19 张），但未建立对应新卡。
Makefile 第 19-20、43、47-48 行仍引用 T-a.md，导致：
- `make thesis` 报错指向不存在的文件
- `make smoke` 报错指向不存在的文件
- `make help` 提示错误

T-ch3/4/5 回填完正文 Markdown 后，必须有工具链把它们转换为最终 Word 文档，
否则论文永远是散落的 .md 文件，无法送审。

## 目标

实现 `scripts/build_thesis.py`，完成：

1. **Markdown → Word 转换**
   - 读取 `thesis/src/*.md`（按章节编号顺序）
   - 替换 `{{n:key}}` 为 `thesis/generated/numbers.json` 中的数值
   - 替换 `{{table:name}}` 为 `thesis/generated/tables/*.csv` 内容
   - 应用 `thesis/template/` 下的北邮模板样式

2. **AUDIT 模式**
   - `make thesis AUDIT=1` 时，在每个数值后附注来源（`[src: path/to/metrics.json]`）
   - 用于答辩前核对数字溯源

3. **冒烟测试**
   - `make smoke` 从 `thesis/smoke.md` 生成 `build/smoke.docx`
   - 验证 pandoc 环境与 reference.docx 模板可用

## 实现

`scripts/build_thesis.py`：

```
thesis/src/*.md ────────────────────┐
thesis/generated/numbers.json ──────┤
thesis/generated/tables/*.csv ──────┼──> build/thesis_V9.docx
thesis/template/reference.docx ─────┘
```

### 核心逻辑

1. 读取所有 Markdown 正文，按章节编号排序
2. 正则匹配 `{{n:([\w.]+)}}`，从 numbers.json 查找替换
3. 正则匹配 `{{table:([\w_]+)}}`，从 tables/ 读取 CSV 并转为 Word 表格
4. 调用 pandoc（或 python-docx）生成 Word，应用 reference.docx 样式
5. AUDIT 模式：替换时在数值后插入来源注释

### 依赖

- pandoc ≥ 2.19（已装）
- python-docx（可选，若 pandoc 表格能力不足）

## 产出

- `scripts/build_thesis.py`
- `thesis/smoke.md`（冒烟测试用 Markdown）
- `thesis/reference.docx`（从 thesis/template/ 复制或创建）
- `build/thesis_V9.docx`（最终论文）
- `build/smoke.docx`（冒烟测试产物）
- `tests/test_build_thesis.py`

## 验收

- [ ] `make thesis` 可从 thesis/src/ 生成 build/thesis_V9.docx
- [ ] 所有 `{{n:key}}` 被正确替换为 numbers.json 中的值
- [ ] 所有 `{{table:name}}` 被正确替换为 Word 表格
- [ ] `make thesis AUDIT=1` 生成的文档包含来源注释
- [ ] `make smoke` 从 thesis/smoke.md 生成 build/smoke.docx
- [ ] pytest 通过（测试替换逻辑与表格生成）

## 简化说明

- 不做 LaTeX 支持（论文用 Word 排版）
- 不做图表自动生成（图由实验卡产出，手动插入或后续扩展）
- 不做目录与页眉页脚自定义（由 reference.docx 模板控制）

## 论文落点

本卡是论文最终产出的**唯一出口**。T-ch3/4/5 回填的 Markdown 正文必须经本卡转换为 .docx 后才能送审。
