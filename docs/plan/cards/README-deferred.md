# 后续整改任务（推迟到送审前）

以下任务不在主路径上，可在核心实验完成后按需补充。

## 研究线

### S-recall-variants 设计变体对比（表 3-9）

- 负向反馈处理方式对比（4 个变体）
- 优先级：低
- 依赖：S-recall-main

### S-recall-new-baseline 近三年强基线

- 候选：XSimGCL、LightGCL、RLMRec
- 优先级：中（整改意见要求）
- 依赖：代码可得性

### S-rank-dien DIEN 基线（推迟到送审前）

- RecBole 1.2.1 内置（`recbole.model.sequential_recommender.dien`），可直接通过 `recbole_baselines.yaml` 训练
- 推迟原因：表 4-1/4-2 的 DIEN 行若留空，答辩时显突兀；但并非核心指标瓶颈
- 依赖：S-rank-base（需与 DIN 共享候选集与候选生成逻辑）

### S-rank-teacher 教师质量评估（表 4-6）

- 生成教师信号，对比学生 AUC
- 优先级：低

### S-rank-e2e 端到端实验（表 4-3、4-4）

- 完整链路评估
- 优先级：低

### S-explain 解释质量评估（表 5-12、5-13）

- BLEU-4、ROUGE-L、人工评估
- 优先级：低

## 工程线

### E-frontend 前端界面

- 截图用于图 5-7 ~ 5-10
- 优先级：低

### E-rag RAG 解释模块

- ChromaDB + Qwen API
- 优先级：低

## 写作线

### T-abstract 摘要撰写

- 待实验数据回填后撰写
- 优先级：高（但依赖实验完成）

### T-refs 参考文献整理

- 扩充到 60-70 篇
- 优先级：中

### T-symbols 符号表

- 统一全文符号
- 优先级：低
