# 工业资产商城推荐系统 MVP

基于"多路召回 → 深度排序 → LLM增强解释"三阶段推荐架构的 Web 原型。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + Vite 6 + TypeScript + Ant Design 5 |
| 后端 | Python 3.12 + FastAPI + Pydantic |
| 依赖管理 | uv (Python) / npm (Node) |
| 数据 | JSON Mock |

## 快速启动

### 后端
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```
Swagger 文档: http://localhost:8000/docs

### 前端
```bash
cd frontend
npm run dev
```
页面: http://localhost:5173

## 页面

| 路由 | 说明 |
|---|---|
| `/` | 首页 - 推荐瀑布流 + 热门商品 |
| `/product/:id` | 商品详情 + 推荐解释 + 相似推荐 |
| `/search?q=xxx` | 搜索结果 + 搜索解释 |
| `/user/:id` | 用户画像 + 行为时间线 + 兴趣标签 |

## API

| 接口 | 说明 |
|---|---|
| `GET /api/products` | 商品列表 |
| `GET /api/products/:id` | 商品详情 |
| `GET /api/recommend` | 个性化推荐 |
| `GET /api/search` | 搜索 |
| `GET /api/users` | 用户列表 |
| `GET /api/users/:id` | 用户详情 |

## 项目结构

```
├── backend/
│   ├── app.py              # FastAPI 入口
│   ├── pyproject.toml      # uv 依赖
│   ├── routes/             # API 路由
│   ├── models/             # Pydantic 模型
│   └── mock/               # Mock 数据
└── frontend/
    ├── src/
    │   ├── App.tsx          # 根组件 (路由/布局)
    │   ├── api/index.ts     # API 封装
    │   └── pages/           # 页面组件
    ├── vite.config.ts       # Vite 配置 (含 API 代理)
    └── package.json
```
