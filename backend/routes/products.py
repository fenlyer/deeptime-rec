import json
from pathlib import Path
from fastapi import APIRouter, Query

from models import Product, ProductListResponse

router = APIRouter(prefix="/api/products", tags=["products"])
_products: list[dict] = []

def _load():
    global _products
    if not _products:
        path = Path(__file__).parent.parent / "mock" / "products.json"
        _products = json.loads(path.read_text())

@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: str = Query("", description="类目筛选"),
    brand: str = Query("", description="品牌筛选"),
    keyword: str = Query("", description="关键词搜索"),
):
    _load()
    filtered = _products
    if category:
        filtered = [p for p in filtered if category in p["category"]]
    if brand:
        filtered = [p for p in filtered if brand in p["brand"]]
    if keyword:
        kw = keyword.lower()
        filtered = [p for p in filtered if kw in p["name"].lower() or kw in p["desc"].lower() or kw in p["category"].lower()]

    total = len(filtered)
    start = (page - 1) * size
    items = filtered[start:start + size]
    return ProductListResponse(total=total, page=page, size=size, items=items)

@router.get("/{product_id}", response_model=Product)
def get_product(product_id: str):
    _load()
    for p in _products:
        if p["id"] == product_id:
            return p
    return None
