# 原型后端（FastAPI）

- **用途**：多路召回 → 深度排序 → LLM 增强解释的三阶段推荐系统 MVP API；依赖锁定用 uv。
- **输入**：`data/processed/` 冻结数据、`results/` 实验产物、LLM 返回。
- **产出**：REST 推荐接口（`/recommend`、`/search`、`/products`、`/user`）。
