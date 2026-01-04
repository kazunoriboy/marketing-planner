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
    review_urls: Optional[Dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# 口コミ関連スキーマ
# ============================================

class ReviewUrlsUpdate(BaseModel):
    """口コミURL更新リクエスト"""
    jalan: Optional[str] = None
    google: Optional[str] = None


class ReviewUrlsResponse(BaseModel):
    """口コミURL取得レスポンス"""
    hotel_id: int
    review_urls: Dict
    updated_at: datetime


class ReviewAnalysisResponse(BaseModel):
    """口コミ分析レスポンス"""
    session_id: int
    reviews_summary: Dict
    sources: List[Dict]
    total_reviews: int
    analyzed_at: datetime


# ============================================
# ペルソナ関連スキーマ
# ============================================

class Persona(BaseModel):
    """ペルソナ（顧客像）"""
    name: str  # 架空の名前
    age_range: str  # 年齢層（例: "30代後半"）
    gender: str  # 性別
    location: str  # 住んでいるところ（例: "東京都世田谷区"）
    occupation: str  # 職業
    travel_purpose: str  # 旅行目的
    values: List[str]  # 価値観・重視すること
    budget_range: str  # 予算帯
    information_source: List[str]  # 情報収集方法
    needs: List[str]  # 宿泊施設に求めること
    pain_points: List[str]  # 悩み・課題
    description: str  # 詳細説明


class PersonaGenerationResponse(BaseModel):
    """ペルソナ生成レスポンス"""
    session_id: int
    personas: List[Persona]
    generated_at: datetime


class PersonasResponse(BaseModel):
    """ペルソナ取得レスポンス"""
    session_id: int
    personas: List[Dict]
    updated_at: Optional[datetime] = None


class PersonaEditRequest(BaseModel):
    """ペルソナ修正リクエスト"""
    persona_index: int  # 修正対象のペルソナのインデックス（0, 1, 2）
    instruction: str  # 修正の指示（例: "もっと若い世代にしてほしい"、"予算を高めに設定してほしい"）


class PersonaEditResponse(BaseModel):
    """ペルソナ修正レスポンス"""
    session_id: int
    persona: Persona  # 修正後のペルソナ
    persona_index: int
    updated_at: datetime
