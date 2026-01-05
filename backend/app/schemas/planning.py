from pydantic import BaseModel, field_validator
from typing import Dict, List, Literal
from datetime import datetime
from app.models import PlanStatus


class PlanGenerationRequest(BaseModel):
    """プラン生成リクエスト"""
    analysis_session_id: int
    num_plans: int = 3  # 生成するプラン数


class PlanSectionEditRequest(BaseModel):
    """プランセクション編集リクエスト"""
    section: Literal["concept", "target_audience", "price_range", "benefits"]
    instruction: str  # 修正指示（例: "地元の名士との交流を削除して、料理体験に焦点を当てて"）
    
    @field_validator("instruction")
    @classmethod
    def instruction_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("修正指示を入力してください")
        return v.strip()


class MarketingPlanResponse(BaseModel):
    """マーケティングプランレスポンス"""
    id: int
    analysis_session_id: int
    status: PlanStatus
    plan_name: str
    concept: str
    target_audience: Dict
    price_range: Dict
    benefits: Dict
    strategy_3c: Dict
    strategy_pest: Dict
    created_at: datetime
    
    class Config:
        from_attributes = True


class PlanApprovalRequest(BaseModel):
    """プラン承認リクエスト"""
    status: PlanStatus


# ============================================
# 既存プラン関連スキーマ
# ============================================

class ExistingPlanCreate(BaseModel):
    """既存プラン作成リクエスト"""
    plan_title: str
    plan_description: str
    room_facilities: List[str] = []  # 部屋の施設・設備
    hotel_assets: List[str] = []  # 宿の活用可能な資産
    price_info: Dict = {}  # 価格情報
    meal_info: Dict = {}  # 食事情報
    notes: str = None


class ExistingPlanUpdate(BaseModel):
    """既存プラン更新リクエスト"""
    plan_title: str = None
    plan_description: str = None
    room_facilities: List[str] = None
    hotel_assets: List[str] = None
    price_info: Dict = None
    meal_info: Dict = None
    notes: str = None
    is_active: bool = None


class ExistingPlanResponse(BaseModel):
    """既存プランレスポンス"""
    id: int
    hotel_id: int
    plan_title: str
    plan_description: str
    room_facilities: List[str]
    hotel_assets: List[str]
    price_info: Dict
    meal_info: Dict
    notes: str = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ExistingPlanBasedGenerationRequest(BaseModel):
    """既存プランベースのプラン生成リクエスト"""
    existing_plan_id: int  # ベースとなる既存プラン
    persona_index: int = None  # ターゲットペルソナ（オプション）
    num_plans: int = 3  # 生成するプラン数

