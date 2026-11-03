import json
from pathlib import Path
from fastapi import APIRouter, Query

from models import RecommendItem, RecommendResponse

router = APIRouter(prefix="/api/recommend", tags=["recommend"])
_rec_data: dict = {}
_products: list[dict] = []

def _load():
    global _rec_data, _products
    if not _rec_data:
        base = Path(__file__).parent.parent / "mock"
        _rec_data = json.loads((base / "recommendations.json").read_text())
        _products = json.loads((base / "products.json").read_text())

def _resolve(product_id: str) -> dict | None:
    for p in _products:
        if p["id"] == product_id:
            return p
    return None

@router.get("", response_model=RecommendResponse)
def get_recommend(
    user_id: str = Query("U001", description="用户ID"),
    scene: str = Query("home", description="场景: home / detail_{product_id}"),
    size: int = Query(10, ge=1, le=50),
):
    _load()
    user_recs = _rec_data.get(user_id, {}).get(scene, [])
    if not user_recs and "detail_" in scene:
        fallback_key = "home"
        user_recs = _rec_data.get(user_id, {}).get(fallback_key, [])

    items = []
    for r in user_recs[:size]:
        prod = _resolve(r["product_id"])
        if prod:
            items.append(RecommendItem(
                product=prod,
                score=r["score"],
                channel=r["channel"],
                explanation=r["explanation"],
            ))
    return RecommendResponse(user_id=user_id, scene=scene, items=items)

@router.get("/scenes")
def list_scenes(user_id: str = Query("U001")):
    _load()
    user_recs = _rec_data.get(user_id, {})
    return {"user_id": user_id, "scenes": list(user_recs.keys())}
