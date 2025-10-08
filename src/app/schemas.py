# src/app/schemas.py
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

class ProjectRead(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class CategoryCreate(BaseModel):
    name: str
    order_index: int = 0

class CategoryRead(BaseModel):
    id: int
    name: str
    order_index: int
    class Config:
        from_attributes = True

class ValueCreate(BaseModel):
    value: str
    risk_weight: int = 1

class ValueRead(BaseModel):
    id: int
    value: str
    risk_weight: int
    class Config:
        from_attributes = True

class GenerateRequest(BaseModel):
    strategy: str  # "all" | "each" | "pairwise"
    limit: Optional[int] = None

class GenerateResponse(BaseModel):
    generation_id: int
    count: int

class TestCaseOut(BaseModel):
    name: str
    assignments: Dict[str, str]
