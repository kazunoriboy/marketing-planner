from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from enum import Enum

if TYPE_CHECKING:
    from typing import List


class PlanStatus(str, Enum):
    """マーケティングプランのステータス"""
    draft = "draft"
    approved = "approved"


class FacilityAdminHotelRole(str, Enum):
    """施設管理者の施設に対する権限"""
    owner = "owner"      # オーナー（全権限）
    editor = "editor"    # 編集者（編集権限）
    viewer = "viewer"    # 閲覧者（閲覧のみ）


# ============================================
# 認証関連モデル
# ============================================

class SystemAdmin(SQLModel, table=True):
    """システム管理者テーブル"""
    __tablename__ = "system_admins"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    is_active: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FacilityAdmin(SQLModel, table=True):
    """施設管理者テーブル"""
    __tablename__ = "facility_admins"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    is_active: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    hotel_permissions: list["FacilityAdminHotel"] = Relationship(back_populates="facility_admin")


class FacilityAdminHotel(SQLModel, table=True):
    """施設管理者と施設の紐付けテーブル（多対多）"""
    __tablename__ = "facility_admin_hotels"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    facility_admin_id: int = Field(foreign_key="facility_admins.id", index=True)
    hotel_id: int = Field(foreign_key="hotels.id", index=True)
    role: FacilityAdminHotelRole = Field(default=FacilityAdminHotelRole.viewer)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    facility_admin: FacilityAdmin = Relationship(back_populates="hotel_permissions")
    hotel: "Hotel" = Relationship(back_populates="admin_permissions")


# ============================================
# 既存モデル
# ============================================

class Hotel(SQLModel, table=True):
    """宿泊施設情報テーブル"""
    __tablename__ = "hotels"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    address: str
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # 宿の特徴や強み（JSON形式）
    features: dict = Field(default_factory=dict, sa_column=Column(JSON))
    strengths: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    analysis_sessions: list["AnalysisSession"] = Relationship(back_populates="hotel")
    admin_permissions: list["FacilityAdminHotel"] = Relationship(back_populates="hotel")


class AnalysisSession(SQLModel, table=True):
    """分析セッションテーブル"""
    __tablename__ = "analysis_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hotel_id: int = Field(foreign_key="hotels.id")
    
    # CSV分析結果
    csv_statistics: dict = Field(default_factory=dict, sa_column=Column(JSON))  # Pandasでの計算結果
    csv_insights: Optional[str] = None  # AIによるインサイト文章
    
    # 市場調査結果
    competitors_list: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 競合リスト
    reviews_summary: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 口コミ要約
    regional_trends: Optional[str] = None  # 地域トレンド
    
    # メタデータ
    analysis_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    hotel: Hotel = Relationship(back_populates="analysis_sessions")
    marketing_plans: list["MarketingPlan"] = Relationship(back_populates="analysis_session")


class MarketingPlan(SQLModel, table=True):
    """マーケティングプランテーブル"""
    __tablename__ = "marketing_plans"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    analysis_session_id: int = Field(foreign_key="analysis_sessions.id")
    
    # プラン基本情報
    status: PlanStatus = Field(default=PlanStatus.draft)
    plan_name: str
    concept: str  # コンセプト文
    
    # ターゲティング
    target_audience: dict = Field(default_factory=dict, sa_column=Column(JSON))  # ターゲット層
    
    # 価格設定
    price_range: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 価格帯
    
    # 特典・特徴
    benefits: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 特典リスト
    
    # 戦略
    strategy_3c: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 3C分析結果
    strategy_pest: dict = Field(default_factory=dict, sa_column=Column(JSON))  # PEST分析結果
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    analysis_session: AnalysisSession = Relationship(back_populates="marketing_plans")
    creative_assets: list["CreativeAsset"] = Relationship(back_populates="marketing_plan")


class CreativeAsset(SQLModel, table=True):
    """制作物テーブル"""
    __tablename__ = "creative_assets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    marketing_plan_id: int = Field(foreign_key="marketing_plans.id")
    
    # LP（ランディングページ）
    lp_source_code: Optional[str] = None  # ReactコンポーネントコードまたはURL
    lp_preview_url: Optional[str] = None
    
    # 広告画像
    ad_image_urls: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 複数の画像URL
    
    # 広告コピー
    ad_copy: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 複数の広告コピー
    
    # 生成メタデータ
    generation_prompts: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 使用したプロンプト
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    marketing_plan: MarketingPlan = Relationship(back_populates="creative_assets")


