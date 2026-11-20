# 原型现状表（E0-a）

复核日期：2026-11-20。用途：确定第五章能写什么、缺什么，以及 5.3.1 表 5-3
「目标架构 vs 原型实现」的对照口径。

## 1. 代码位置

原型全部在 `backend/`（FastAPI），前端在 `frontend/`（React 18 + Vite）。
`serving/` 目录只有 README 与 `explain/`（空），**E-serve 卡要新建的还是改造 backend/，需先定**。

| 位置 | 文件 | 行数级别 | 说明 |
|-----|------|---------|------|
| `backend/app.py` | FastAPI 实例 | ~30 | CORS、4 个 router 挂载、`/api/health` |
| `backend/routes/recommend.py` | `/api/recommend`、`/api/recommend/scenes` | ~50 | **读 mock JSON**，非模型推理 |
| `backend/routes/products.py` | `/api/products`、`/api/products/{id}` | ~45 | 类目/品牌/关键词筛选 + 分页 |
| `backend/routes/search.py` | `/api/search` | ~55 | 关键词打分排序 + 行业偏好话术 |
| `backend/routes/user.py` | `/api/users`、`/{id}`、`/{id}/history`、`/{id}/tags` | ~60 | 用户画像 + 行为历史 |
| `backend/models/__init__.py` | Pydantic 模型 | ~67 | Product / RecommendItem / UserProfile 等 7 个 |
| `backend/mock/*.json` | 4 份 mock 数据 | — | users / products / interactions / recommendations |

## 2. 已实现 vs 论文第五章的描述

| 论文描述 | 原型现状 | 差距 |
|---------|---------|------|
| 四路异构召回 | ❌ 无。`recommend.py` 直接读 `mock/recommendations.json` 里写好的结果 | 需 E-serve 实现 |
| TI-LightGCN 图嵌入召回 | ❌ 无模型、无 FAISS | 需 S-recall-main 产出嵌入 |
| 语义近邻召回（User Memory） | ❌ 无 | 需 S-rank-distill 产出向量 |
| I2I 协同召回 | ❌ 无 | 需 E-serve |
| 类目兜底召回 | ❌ 无 | 需 E-serve |
| Temporal-DIN 精排 | ❌ 无 | 需 S-rank-main |
| 语义重排序 | ❌ 无 | 需 E-serve |
| LLM 推荐解释 | ⚠️ 字段存在（`RecommendItem.explanation`），但取自 mock JSON，非实时生成 | 需 E-rag（已推迟） |
| 行为埋点接口 | ❌ 无（`/api/behavior` 不存在） | 需 E-serve |
| 在线缓存 | ❌ 无 | 需 E-serve |
| 离线调度 | ❌ 无 | 需 E-serve |
| 降级与容错 | ⚠️ 仅 `recommend.py` 里 scene 未命中时回退到 `home` | 需 E-serve |
| 分页 / 类目筛选 / 关键词搜索 | ✅ 有（products 与 search） | — |
| 用户画像与行为时间线 | ✅ 有（user.py，返回 long/short_term_tags 与 history） | — |

## 3. 接口清单（实际路径，以代码为准）

| 实际路径 | 方法 | 论文表 5-7 写法 | 结论 |
|---------|------|----------------|------|
| `/api/recommend` | GET | `/api/recommend` | ✅ 一致 |
| `/api/recommend/scenes` | GET | 未列出 | 表 5-7 可补，或删 |
| `/api/recommend/explain` | — | `/api/recommend/explain` | ❌ **不存在** |
| `/api/products` | GET | `/api/products` | ✅ 一致 |
| `/api/products/{id}` | GET | 未列出 | 表 5-7 可补 |
| `/api/search` | GET | `/api/search` | ✅ 一致 |
| `/api/users` | GET | 未列出 | 表 5-7 可补 |
| `/api/users/{user_id}` | GET | `/api/users/{user_id}` | ✅ 一致 |
| `/api/users/{id}/history` | GET | 未列出 | 表 5-7 可补 |
| `/api/users/{id}/tags` | GET | 未列出 | 表 5-7 可补 |
| `/api/health` | GET | 未列出 | 表 5-7 可补 |
| `/api/behavior/track` | — | 表 5-8 写作 `/api/behavior/track` | ❌ **不存在** |

⚠ 论文正文 5.3.3 与表 5-8 另写作 `/api/rec/recommend`、`/api/rec/explain`，与实际代码三者不一致。
**以代码为准统一为 `/api/recommend`**（无 `/rec` 前缀）。

## 4. 数据来源

| mock 文件 | 内容 | 与 Amazon IS 的关系 |
|----------|------|-------------------|
| `users.json` | 用户画像（姓名、行业、公司规模、岗位、长短期标签） | 无。IS 不含注册行业信息 |
| `products.json` | 商品（类目、品牌、价格、参数、库存） | 无。IS 商品名为英文标题 |
| `interactions.json` | 用户行为（user_id, product_id, action, timestamp） | 无 |
| `recommendations.json` | 预生成的推荐（product_id, score, channel, explanation） | 无 |

结论：**原型是演示数据，不是 IS 数据集上的模型输出**。第五章表 5-3 已用「目标架构 vs 原型实现」
两列处理这一差距，但 5.6 平台展示的四张截图若基于 mock 数据，需在图注说明「演示数据」。

## 5. 对第五章写作的影响

1. **5.3.1 表 5-3** 可保留（目标架构 vs 原型实现对照），但「原型实现」列须与本节一致。
2. **5.4 核心模块实现** 目前无内容可写——表 5-8 列出的 `core/recall.py`、`core/ti_lightgcn.py`
   等 15 个文件全部不存在。E-serve 必须真正实现这些文件，否则 5.4 整节落空。
3. **5.5.5 推荐解释质量评估**（表 5-12/5-13）依赖真实 LLM 调用与人工标注，原型只有 mock 文本 → 已列入推迟。
4. **5.6 平台展示**（图 5-7~5-10）可用现有 `frontend/` 截图，但须在图注写明演示数据来源。

## 6. E-serve 卡片需要补充的决策

- [ ] 改造 `backend/` 还是新建 `serving/`？（建议改造 backend/，避免两套并存）
- [ ] `frontend/` 是否直接用于 5.6 截图？（若否，5.6 整节删除）
- [ ] mock 数据是否替换为 IS 训练集抽样？（建议：替换为 IS 真实用户/商品，成本低且与论文一致）
