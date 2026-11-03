from pydantic import BaseModel
from typing import Optional

class Product(BaseModel):
    id: str
    name: str
    category: str
    brand: str
    price: float
    image: str
    tags: list[str]
    params: dict[str, str]
    stock: int
    desc: str

class ProductListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[Product]

class RecommendItem(BaseModel):
    product: Product
    score: float
    channel: str
    explanation: str

class RecommendResponse(BaseModel):
    user_id: str
    scene: str
    items: list[RecommendItem]

class SearchItem(BaseModel):
    product: Product
    score: float

class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    size: int
    items: list[SearchItem]
    explanation: str

class Interaction(BaseModel):
    user_id: str
    product_id: str
    action: str
    timestamp: str

class UserProfile(BaseModel):
    id: str
    name: str
    industry: str
    company: str
    company_scale: str
    role: str
    long_term_tags: list[str]
    short_term_tags: list[str]
    avatar: str

class UserDetailResponse(BaseModel):
    user: UserProfile
    history: list[Interaction]
    long_term_tags: list[str]
    short_term_tags: list[str]
