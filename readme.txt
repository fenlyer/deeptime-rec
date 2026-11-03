### 项目总览

deeptime-rec/
├── backend/                                  # FastAPI + uv[cite: 1]
│   ├── app.py                                # 入口，含 CORS + Swagger[cite: 1]
│   ├── pyproject.toml                        # uv 依赖声明[cite: 1]
│   └── routes/                               # 4 个路由模块[cite: 1]
│       ├── products.py                       # GET /api/products[cite: 1]
│       ├── recommend.py                      # GET /api/recommend[cite: 1]
│       ├── search.py                         # GET /api/search[cite: 1]
│       └── user.py                           # GET /api/users[cite: 1]
├── models/__init__.py                        # Pydantic 数据模型[cite: 1]
└── mock/                                     # 40条商品 + 5个用户 + 推荐数据[cite: 1]

└── frontend/                                 # React + Vite + Ant Design[cite: 1]
    └── src/                                  
        ├── App.tsx                           # 布局 + 路由 + 用户切换[cite: 1]
        ├── api/index.ts                      # Axios 封装[cite: 1]
        └── pages/                            
            ├── Home.tsx                      # 推荐瀑布流（多路召回标签 + 解释）[cite: 1]
            ├── ProductDetail.tsx             # 商品详情 + 推荐解释 + 看了又看[cite: 1]
            ├── SearchResult.tsx              # 搜索结果 + 搜索解释[cite: 1]
            └── UserProfile.tsx               # 行为时间线 + 长短兴趣标签[cite: 1]


### 启动方式

# 终端 1 - 后端
cd backend && uv run uvicorn app:app --reload --port 8000

# 终端 2 - 前端
cd frontend && npm run dev

访问 http://localhost:5173 即可看到原型。顶部右上角可切换 5 个用户身份，首页推荐和搜索解释都会随之变化。

### 核心特性

- 召回通道可视化：每个推荐卡片标注召回来源（时序协同/物品协同/用户协同/热门/内容相似），对应论文的三阶段架构
- 推荐解释：卡片和详情页均展示推荐理由，可解释性一目了然
- 用户画像：长短期兴趣标签分离展示，对应论文的时序兴趣建模
- Swagger 文档：/docs 可交互调试所有接口
