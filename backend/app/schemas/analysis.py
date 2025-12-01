from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class CSVAnalysisRequest(BaseModel):
    """CSV分析リクエスト"""
    hotel_id: int


class CSVAnalysisResponse(BaseModel):
    """CSV分析レスポンス"""
    session_id: int
    statistics: Dict
    insights: str
    created_at: datetime


class MarketResearchRequest(BaseModel):
    """市場調査リクエスト"""
    hotel_id: int
    address: str
    radius_km: Optional[float] = 5.0  # デフォルト5km圏内


class MarketResearchResponse(BaseModel):
    """市場調査レスポンス"""
    session_id: int
    competitors: Dict
    reviews_summary: Dict
    regional_trends: str
    created_at: datetime


class HotelCreate(BaseModel):
    """宿泊施設作成リクエスト"""
    name: str
    address: str
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    features: Optional[Dict] = None
    strengths: Optional[Dict] = None


class HotelResponse(BaseModel):
    """宿泊施設レスポンス"""
    id: int
    name: str
    address: str
    postal_code: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    features: Dict
    strengths: Dict
    created_at: datetime
    
    class Config:
        from_attributes = True


