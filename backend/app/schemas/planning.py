from pydantic import BaseModel
from typing import Dict, List
from datetime import datetime
from app.models import PlanStatus


class PlanGenerationRequest(BaseModel):
    """プラン生成リクエスト"""
    analysis_session_id: int
    num_plans: int = 3  # 生成するプラン数


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
    plan_id: int
    status: PlanStatus


