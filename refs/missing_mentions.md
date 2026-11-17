# 正文提到但缺少对应文献条目的名词

以下名词在正文中被提及，但在 43 条参考文献中找不到对应条目。
请在 DBLP / 知网核查后补入 refs/thesis.bib，或在正文中改为有引用的表述。

## 模型 / 方法

| 名词 | 正文上下文 | 建议处理 |
|------|-----------|---------|
| **KGCN** | "将图神经网络与知识图谱融合（KGCN、RippleNet）" | 补引用：Wang et al., KGCN, WWW 2019 |
| **GPT4Rec** | "代表工作包括 GPT4Rec、TALLRec 等" | 补引用：Hua et al., GPT4Rec, WWW 2024 |
| **GPT-4** | "以 GPT-4、LLaMA-2、Qwen 为代表的大语言模型" | 补引用：OpenAI, GPT-4 Technical Report, 2023 |
| **LLaMA-2** | 同上 | 补引用：Touvron et al., Llama 2, arXiv 2307.09288 |
| **MBGCN** | "MBGCN（Multi-Behavior Graph Collaborative…" | 补引用：Jin et al., MBGCN, SIGIR 2020 |

## 数据集

| 名词 | 正文上下文 | 说明 |
|------|-----------|------|
| **IS / TH / OP / AJ** | 本文 4 个数据集的缩写 | 不需要引用，但首次出现需写明全称和来源（Amazon 2023） |
| **Amazon 2023** | "Amazon 2023 的 Industrial & Scientific" | 补引用或写明下载链接（zhengnian1998/Amazon-2023-on-HuggingFace） |

## 路线图建议补入的高优先文献（§2.1 必补项）

以下来自 `docs/report/论文水平提升分析报告.html` §2.1，当前 43 条中均未覆盖：

- 多行为图推荐：MBGCN、KHGT、CML
- 时间感知图/序列：TGSRec、TiSASRec
- LLM 画像 + 对齐：RLMRec 系列
- 生成式推荐：TIGER、LC-Rec、OneRec / HSTU
- RAG 解释：2024–2025 的 RAG-based explanation
- 与本文最接近的工作：KAR、DLLM2Rec、孙浩然 2025
