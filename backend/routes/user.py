import json
from pathlib import Path
from fastapi import APIRouter, Query

from models import UserProfile, UserDetailResponse, Interaction

router = APIRouter(prefix="/api/users", tags=["users"])
_users: list[dict] = []
_interactions: list[dict] = []

def _load():
    global _users, _interactions
    if not _users:
        base = Path(__file__).parent.parent / "mock"
        _users = json.loads((base / "users.json").read_text())
        _interactions = json.loads((base / "interactions.json").read_text())

@router.get("")
def list_users():
    _load()
    return [{"id": u["id"], "name": u["name"], "role": u["role"], "industry": u["industry"]} for u in _users]

@router.get("/{user_id}", response_model=UserDetailResponse)
def get_user(user_id: str):
    _load()
    user = next((u for u in _users if u["id"] == user_id), None)
    if not user:
        return None

    history = sorted(
        [i for i in _interactions if i["user_id"] == user_id],
        key=lambda x: x["timestamp"],
        reverse=True,
    )
    return UserDetailResponse(
        user=user,
        history=history[:20],
        long_term_tags=user["long_term_tags"],
        short_term_tags=user["short_term_tags"],
    )

@router.get("/{user_id}/history")
def get_user_history(user_id: str, limit: int = Query(20, le=50)):
    _load()
    history = sorted(
        [i for i in _interactions if i["user_id"] == user_id],
        key=lambda x: x["timestamp"],
        reverse=True,
    )
    return {"user_id": user_id, "history": history[:limit]}

@router.get("/{user_id}/tags")
def get_user_tags(user_id: str):
    _load()
    user = next((u for u in _users if u["id"] == user_id), None)
    if not user:
        return None
    return {
        "user_id": user_id,
        "long_term_tags": user["long_term_tags"],
        "short_term_tags": user["short_term_tags"],
    }
