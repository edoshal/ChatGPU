from typing import Any, Dict, List, Optional
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, validator


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


# === HEALTH PLANNING MODELS ===

class GoalType(str, Enum):
    """Loại mục tiêu sức khỏe"""
    WEIGHT_GAIN = "weight_gain"
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    ENDURANCE = "endurance"
    RECOVERY = "recovery"
    MAINTENANCE = "maintenance"

class PlanStatus(str, Enum):
    """Trạng thái kế hoạch"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class IntensityLevel(str, Enum):
    """Mức độ cường độ"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MealType(str, Enum):
    """Loại bữa ăn"""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"

class HealthPlanCreate(BaseModel):
    """Tạo kế hoạch sức khỏe mới"""
    title: str = Field(..., min_length=1, max_length=200)
    goal_type: GoalType
    target_value: float = Field(..., gt=0)
    target_unit: str = Field(..., min_length=1)  # kg, %, days, etc.
    duration_days: int = Field(..., gt=0, le=365)
    start_date: date
    available_activities: List[str] = Field(default_factory=list)  # ["swimming", "football", "gym"]
    dietary_restrictions: List[str] = Field(default_factory=list)  # ["vegetarian", "no_dairy"]
    notes: Optional[str] = None

class HealthPlanUpdate(BaseModel):
    """Cập nhật kế hoạch sức khỏe"""
    title: Optional[str] = None
    status: Optional[PlanStatus] = None
    current_progress: Optional[float] = None
    notes: Optional[str] = None

class ActivityCreate(BaseModel):
    """Tạo hoạt động trong kế hoạch"""
    date: date
    activity_type: str = Field(..., min_length=1)
    activity_name: str = Field(..., min_length=1)
    duration_minutes: int = Field(..., gt=0)
    intensity: IntensityLevel
    calories_target: Optional[float] = None
    instructions: Optional[str] = None

class ActivityUpdate(BaseModel):
    """Cập nhật hoạt động trong kế hoạch"""
    activity_type: Optional[str] = None
    activity_name: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    intensity: Optional[IntensityLevel] = None
    calories_target: Optional[float] = None
    instructions: Optional[str] = None

class ActivityLog(BaseModel):
    """Ghi nhận hoạt động đã thực hiện"""
    activity_plan_id: Optional[int] = None
    date: date
    activity_type: str
    activity_name: str
    duration_minutes: int
    intensity: IntensityLevel
    calories_burned: Optional[float] = None
    notes: Optional[str] = None
    source: str = "manual"  # manual, chat, auto

class MealCreate(BaseModel):
    """Tạo bữa ăn trong kế hoạch"""
    date: date
    meal_type: MealType
    food_items: List[Dict[str, Any]]  # [{"name": "rice", "amount": "100g", "calories": 130}]
    total_calories: Optional[float] = None
    macros: Optional[Dict[str, float]] = None  # {"protein": 20, "carbs": 50, "fat": 10}
    preparation_notes: Optional[str] = None

class MealLog(BaseModel):
    """Ghi nhận bữa ăn đã thực hiện"""
    meal_plan_id: Optional[int] = None
    date: date
    meal_type: MealType
    food_items: List[Dict[str, Any]]
    total_calories: Optional[float] = None
    notes: Optional[str] = None
    source: str = "manual"  # manual, chat, auto

class HealthPlan(BaseModel):
    """Kế hoạch sức khỏe đầy đủ"""
    id: int
    health_profile_id: int
    title: str
    goal_type: GoalType
    target_value: float
    target_unit: str
    duration_days: int
    start_date: date
    end_date: date
    current_progress: float
    status: PlanStatus
    available_activities: List[str]
    dietary_restrictions: List[str]
    ai_analysis: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class DailyPlanSummary(BaseModel):
    """Tóm tắt kế hoạch hàng ngày"""
    date: date
    activities: List[Dict[str, Any]]
    meals: List[Dict[str, Any]]
    total_calories_target: float
    total_calories_actual: Optional[float] = None
    completion_rate: float  # 0-100%

