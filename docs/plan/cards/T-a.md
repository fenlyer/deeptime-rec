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
