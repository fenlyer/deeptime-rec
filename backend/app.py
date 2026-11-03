from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import products, recommend, search, user

app = FastAPI(
    title="工业资产商城推荐系统 MVP",
    description="多路召回 → 深度排序 → LLM增强解释 三阶段推荐架构原型",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(recommend.router)
app.include_router(search.router)
app.include_router(user.router)

@app.get("/api/health")
def health():
    return {"status": "ok"}
