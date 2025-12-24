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


