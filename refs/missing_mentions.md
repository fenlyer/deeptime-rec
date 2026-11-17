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

## thesis.bib已补充清单
| 名词  | 正文上下文 | 真实文献与 BibTeX Key | 官方 DOI / 链接 |
| --- | --- | --- | --- |
| **KGCN** | "将图神经网络与知识图谱融合（KGCN、RippleNet）" | Wang et al., WWW 2019 (`wang2019kgcn`) | `10.1145/3308558.3313417` |
| **GPT4Rec** | "代表工作包括 GPT4Rec、TALLRec 等" | Li et al., arXiv 2023 (`li2023gpt4rec`) | `https://arxiv.org/abs/2304.03879` |
| **GPT-4** | "以 GPT-4、LLaMA-2、Qwen 为代表的大语言模型" | OpenAI, Technical Report 2023 (`openai2023gpt4`) | `https://arxiv.org/abs/2303.08774` |
| **LLaMA-2** | 同上  | Touvron et al., arXiv 2023 (`touvron2023llama2`) | `https://arxiv.org/abs/2307.09288` |
| **MBGCN** | "MBGCN（Multi-Behavior Graph Collaborative…" | Jin et al., SIGIR 2020 (`jin2020mbgcn`) | `10.1145/3397271.3401077` |

1. **多行为图推荐**：
  - `xia2021khgt`：KHGT (ICDE 2021, DOI: `10.1109/ICDE51399.2021.00179`)
  - `wei2022cml`：CML (WSDM 2022, DOI: `10.1145/3488560.3498527`)
2. **时间感知图与序列推荐**：
  - `fan2021tgsrec`：TGSRec (CIKM 2021, DOI: `10.1145/3459637.3482242`)
  - `li2020tisasrec`：TiSASRec (WSDM 2020, DOI: `10.1145/3336191.3371786`)
3. **LLM 画像对齐与知识蒸馏（与本文 Temporal-DIN+LLM蒸馏 核心强相关）**：
  - `ren2024rlmrec`：RLMRec (WWW 2024, DOI: `10.1145/3589334.3645458`)
  - `xi2024kar`：KAR (RecSys 2024, DOI: `10.1145/3640457.3688104`)
  - `cui2024dllm2rec`：DLLM2Rec (RecSys 2024, DOI: `10.1145/3640457.3688116`)
  - `sheng2024slmrec`：SLMRec — 大模型蒸馏至小序列推荐模型 (ICLR 2025, `arXiv:2405.17890`)
  - `li2024ctrl`：CTRL (ACM TOIS 2024, DOI: `10.1145/3631942`)
  - `wei2024llmrec`：LLMRec (WSDM 2024, DOI: `10.1145/3616855.3635853`)
  - `lin2024rella`：ReLLa (WWW 2024, DOI: `10.1145/3589334.3645481`)
  - `liu2024once`：ONCE (WSDM 2024, DOI: `10.1145/3616855.3635845`)
  - `yang2024unirec`：Aligning LLMs with Rec Knowledge (ACL Findings 2024, DOI: `10.18653/v1/2024.findings-acl.630`)
  - `sheng2024alpharec`：AlphaRec (ICLR 2025, `arXiv:2407.05441`)
4. **生成式推荐（前沿范式对比）**：
  - `rajput2023tiger`：TIGER (NeurIPS 2023, `arXiv:2305.05065`)
  - `zheng2024lcrec`：LC-Rec (ICDE 2024, DOI: `10.1109/ICDE60146.2024.00118`)
  - `zhai2024hstu`：HSTU (ICML 2024, `arXiv:2402.17152`)
  - `wang2024letter`：LETTER (CIKM 2024, DOI: `10.1145/3627673.3679569`)
5. **RAG 解释与大模型推荐综述（2023–2024）**：
  - `wang2024xrec`：XRec (EMNLP Findings 2024, DOI: `10.18653/v1/2024.findings-emnlp.22`)
  - `lubos2024llmexplain`：LLM-generated Explanations (UMAP 2024, DOI: `10.1145/3631700.3665185`)
  - `di2023ragexplain`：RAG Recommender Systems (RecSys 2023, DOI: `10.1145/3604915.3608889`)
  - `wu2024surveyllmrec`：A Survey on LLMs for Recommendation (World Wide Web 2024, DOI: `10.1007/s11280-024-01291-2`)
  - `wang2024llm2vec`：LLM2Vec (ACL 2024, DOI: `10.18653/v1/2024.acl-long.642`)

  