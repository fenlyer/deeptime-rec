# artifacts_llm/ — LLM 中间产物

- **用途**：存放 User Memory 等 LLM 离线产物，供训练与导出复用。
- **输入**：`llm/build_memory.py` 的批量推理结果。
- **产出**：`user_memory.jsonl`（每行带 data tag、模型 revision、prompt 版本）、`memory_emb.npy`。