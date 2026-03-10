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


class OperationManualStatus(str, Enum):
    """オペレーションマニュアルのステータス"""
    in_progress = "in_progress"  # チャット進行中
    completed = "completed"       # マニュアル生成完了


class FacilityAdminHotelRole(str, Enum):
    """施設管理者の施設に対する権限"""
    owner = "owner"      # オーナー（全権限）
    editor = "editor"    # 編集者（編集権限）
    viewer = "viewer"    # 閲覧者（閲覧のみ）


# ============================================
# 認証関連モデル
# ============================================

class Company(SQLModel, table=True):
    """企業グループテーブル"""
    __tablename__ = "companies"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    facility_admins: list["FacilityAdmin"] = Relationship(back_populates="company")


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
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id", index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    company: Optional["Company"] = Relationship(back_populates="facility_admins")
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
    
    # 口コミURL（複数サイト対応）
    # 例: {"jalan": "https://...", "google": "https://..."}
    review_urls: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    # CV用URL（LP生成時に使用される予約リンク）
    # 例: "https://www.jalan.net/yad123456/"
    cv_url: Optional[str] = None
    
    # 施設の資産情報（JSON形式）
    # 施設が提供できるもの（設備、備品、料理など）をカテゴリ別に管理
    # {
    #   "room_amenities": ["露天風呂", "マッサージチェア", "加湿器", "コーヒーメーカー"],
    #   "shared_facilities": ["大浴場", "貸切風呂", "サウナ", "エステ", "庭園", "足湯"],
    #   "dining": ["和朝食", "洋朝食", "会席料理", "鉄板焼き", "バイキング", "部屋食対応"],
    #   "services": ["送迎", "荷物預かり", "ルームサービス", "マッサージ", "ベビーシッター"],
    #   "experiences": ["陶芸体験", "そば打ち体験", "農業体験", "釣り", "クルージング"]
    # }
    hotel_assets: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    # 施設画像（最大10件）。各要素: key, url, description, type, order
    facility_images: list = Field(default_factory=list, sa_column=Column(JSON))

    # 宿のストーリー・周辺情報（JSON形式）
    # {
    #   "story":      "創業〇〇年。山の麓に佇む...",
    #   "highlights": ["源泉かけ流し", "地産地消料理"],
    #   "surrounding": {
    #     "description": "南アルプスの麓に位置し...",
    #     "attractions": [
    #       {"name": "○○温泉郷", "distance": "徒歩5分"},
    #       {"name": "△△神社",   "distance": "車10分"}
    #     ]
    #   },
    #   "access": "新宿駅から特急で2時間。送迎あり（要予約）"
    # }
    hotel_detail: dict = Field(default_factory=dict, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    analysis_sessions: list["AnalysisSession"] = Relationship(back_populates="hotel")
    admin_permissions: list["FacilityAdminHotel"] = Relationship(back_populates="hotel")
    csv_upload_histories: list["CSVUploadHistory"] = Relationship(back_populates="hotel")


class CSVUploadHistory(SQLModel, table=True):
    """CSVアップロード履歴テーブル
    
    CSVファイルをアップロードするたびに1レコード作成され、
    個別の統計情報を保持する。AnalysisSessionには合算した統計が保存される。
    """
    __tablename__ = "csv_upload_histories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hotel_id: int = Field(foreign_key="hotels.id", index=True)
    
    # ファイル情報
    filename: str  # アップロードしたファイル名
    file_hash: Optional[str] = None  # ファイルのハッシュ値（重複検知用）
    
    # データ期間（重複チェック用）
    # CSVから抽出した宿泊日の範囲
    data_period_start: Optional[datetime] = None  # データ期間の開始日
    data_period_end: Optional[datetime] = None    # データ期間の終了日
    
    # 統計情報（このCSV単体の統計）
    statistics: dict = Field(default_factory=dict, sa_column=Column(JSON))
    record_count: int = Field(default=0)  # レコード数
    
    # 移行フラグ
    is_migrated: bool = Field(default=False)  # システム移行により作成されたか
    
    # メモ
    notes: Optional[str] = None
    
    # メタデータ
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    hotel: "Hotel" = Relationship(back_populates="csv_upload_histories")


class AnalysisSession(SQLModel, table=True):
    """分析セッションテーブル"""
    __tablename__ = "analysis_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hotel_id: int = Field(foreign_key="hotels.id")
    
    # CSV分析結果
    csv_statistics: dict = Field(default_factory=dict, sa_column=Column(JSON))  # Pandasでの計算結果（合算）
    csv_insights: Optional[str] = None  # AIによるインサイト文章
    csv_upload_count: int = Field(default=0)  # CSVアップロード回数
    
    # 市場調査結果
    competitors_list: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 競合リスト
    reviews_summary: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 口コミ要約
    regional_trends: Optional[str] = None  # 地域トレンド
    
    # ペルソナ（顧客像）
    # [
    #   {
    #     "name": "田中花子",
    #     "age_range": "30代後半",
    #     "gender": "女性",
    #     "occupation": "会社員（営業職）",
    #     "travel_purpose": "週末リフレッシュ",
    #     "values": ["温泉でゆっくり", "美味しい料理", "非日常体験"],
    #     "budget_range": "1泊2万〜3万円",
    #     "information_source": ["じゃらん", "Instagram", "友人の口コミ"],
    #     "needs": ["清潔感のある部屋", "地元食材を使った料理", "夜遅くまでチェックイン可能"],
    #     "pain_points": ["平日は忙しい", "休日の予約が取りにくい"],
    #     "description": "ペルソナの詳細説明"
    #   },
    #   ...
    # ]
    personas: list = Field(default_factory=list, sa_column=Column(JSON))
    
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
    # analysis_session_idはOptional（既存プランベースの生成では分析セッションがない場合がある）
    analysis_session_id: Optional[int] = Field(default=None, foreign_key="analysis_sessions.id")
    
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
    operation_manual: Optional["OperationManual"] = Relationship(back_populates="marketing_plan")


class CreativeAsset(SQLModel, table=True):
    """制作物テーブル"""
    __tablename__ = "creative_assets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    marketing_plan_id: int = Field(foreign_key="marketing_plans.id")
    
    # LP（ランディングページ）
    lp_source_code: Optional[str] = None  # HTML + CSS + JSシングルファイルのソースコード
    lp_preview_url: Optional[str] = None
    
    # LP用画像
    lp_image_urls: dict = Field(default_factory=dict, sa_column=Column(JSON))  # LP用画像URL
    
    # 広告画像
    ad_image_urls: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 広告用画像URL
    
    # 広告コピー
    ad_copy: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 複数の広告コピー
    
    # OTAテキスト（じゃらん、楽天トラベル向け）
    # {"jalan": {...}, "rakuten": {...}}
    ota_text: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    # 生成メタデータ
    generation_prompts: dict = Field(default_factory=dict, sa_column=Column(JSON))  # 使用したプロンプト
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    marketing_plan: MarketingPlan = Relationship(back_populates="creative_assets")


class OperationManual(SQLModel, table=True):
    """オペレーションマニュアルテーブル"""
    __tablename__ = "operation_manuals"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    marketing_plan_id: int = Field(foreign_key="marketing_plans.id", index=True)
    
    # ステータス
    status: OperationManualStatus = Field(default=OperationManualStatus.in_progress)
    
    # マニュアル内容（JSON形式）
    # {
    #   "title": "マニュアルタイトル",
    #   "overview": "概要",
    #   "phases": [
    #     {
    #       "name": "準備フェーズ",
    #       "tasks": [
    #         {"title": "タスク名", "description": "説明", "estimated_time": "1時間", "responsible": "担当者"},
    #         ...
    #       ]
    #     },
    #     ...
    #   ],
    #   "timeline": "タイムライン",
    #   "notes": "備考"
    # }
    manual_content: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    # チャットから抽出した施設の状況
    # {
    #   "current_tools": ["じゃらん", "Googleビジネスプロフィール"],
    #   "staff_situation": "担当者1名、マーケティング経験なし",
    #   "budget": "月5万円程度",
    #   "challenges": ["SNS運用が苦手", "写真撮影のスキルがない"],
    #   ...
    # }
    facility_context: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    marketing_plan: MarketingPlan = Relationship(back_populates="operation_manual")
    chat_messages: list["OperationChatMessage"] = Relationship(back_populates="operation_manual")


class OperationChatMessage(SQLModel, table=True):
    """オペレーションチャットメッセージテーブル"""
    __tablename__ = "operation_chat_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    operation_manual_id: int = Field(foreign_key="operation_manuals.id", index=True)
    
    # メッセージ
    role: str  # "user" or "assistant"
    content: str
    
    # メタデータ（AIの思考プロセスなど）
    msg_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    operation_manual: OperationManual = Relationship(back_populates="chat_messages")


class ExistingPlan(SQLModel, table=True):
    """既存プラン（宿が現在運用しているプラン）テーブル
    
    宿が既に運用しているプランを登録し、
    そのプランの見せ方を変えたマーケティングプランを生成するために使用
    """
    __tablename__ = "existing_plans"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hotel_id: int = Field(foreign_key="hotels.id", index=True)
    
    # プラン基本情報
    plan_title: str  # プランのタイトル
    plan_description: str  # プランの説明文
    
    # 部屋についている施設・設備（JSON配列）
    # 例: ["露天風呂", "マッサージチェア", "ミニバー", "加湿器"]
    room_facilities: list = Field(default_factory=list, sa_column=Column(JSON))
    
    # 宿自体の活用可能な資産（JSON配列）
    # 例: ["大浴場", "貸切風呂", "レストラン", "バー", "エステ", "庭園", "足湯"]
    hotel_assets: list = Field(default_factory=list, sa_column=Column(JSON))
    
    # 現在の価格帯（参考情報）
    # {"min": 10000, "max": 30000, "standard": 20000}
    price_info: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    # 食事に関する情報
    # {"breakfast": "和洋バイキング", "dinner": "会席料理", "options": ["部屋食可", "アレルギー対応"]}
    meal_info: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    # その他特記事項
    notes: Optional[str] = None
    
    # メタデータ
    is_active: bool = Field(default=True)  # 現在運用中かどうか
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # リレーション
    hotel: Hotel = Relationship()

