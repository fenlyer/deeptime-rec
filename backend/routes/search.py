import json
from pathlib import Path
from fastapi import APIRouter, Query

from models import SearchItem, SearchResponse

router = APIRouter(prefix="/api/search", tags=["search"])
_products: list[dict] = []

def _load():
    global _products
    if not _products:
        _products = json.loads((Path(__file__).parent.parent / "mock" / "products.json").read_text())

@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(..., description="搜索关键词"),
    user_id: str = Query("U001", description="用户ID"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    _load()
    kw = q.lower()
    results = []
    for p in _products:
        score = 0.0
        if kw in p["name"].lower():
            score = 0.95
        elif kw in p["category"].lower():
            score = 0.80
        elif kw in p["brand"].lower():
            score = 0.75
        elif kw in p["desc"].lower():
            score = 0.60
        elif any(kw in v.lower() for v in p["params"].values()):
            score = 0.45
        if score > 0:
            results.append((p, score))

    results.sort(key=lambda x: x[1], reverse=True)
    total = len(results)
    start = (page - 1) * size
    page_items = results[start:start + size]

    industry_map = {"U001": "化工", "U002": "汽车零部件", "U003": "食品饮料", "U004": "电子制造", "U005": "水处理"}
    industry = industry_map.get(user_id, "")

    return SearchResponse(
        query=q,
        total=total,
        page=page,
        size=size,
        items=[SearchItem(product=p, score=s) for p, s in page_items],
        explanation=f"结合您的「{industry}」行业偏好，优先展示相关品类商品" if industry else "",
    )
