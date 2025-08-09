from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class UserProfile(BaseModel):
    id: int
    name: str
    age: Optional[int] = None
    conditions_text: str = ""
    conditions_json: Dict[str, Any] = {}


class FoodItem(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    nutrients: Dict[str, Any] = {}
    contraindications: Optional[str] = None
    recommended_portion: Optional[str] = None
    notes: Optional[str] = None


