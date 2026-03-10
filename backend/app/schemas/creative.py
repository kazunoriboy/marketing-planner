from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime


class CreativeGenerationRequest(BaseModel):
    """クリエイティブ生成リクエスト"""
    marketing_plan_id: int
    generate_lp: bool = True  # LPを生成するか
    generate_images: bool = True  # 画像を生成するか
    generate_ad_copy: bool = True  # 広告コピーを生成するか


class LpRevisionEntry(BaseModel):
    """LP修正履歴エントリ"""
    revision_id: str
    instruction: str
    summary: str
    timestamp: str
    lp_source_code: str


class LpAdjustRequest(BaseModel):
    """LP調整リクエスト"""
    instruction: str


class CreativeAssetResponse(BaseModel):
    """クリエイティブアセットレスポンス"""
    id: int
    marketing_plan_id: int
    lp_source_code: Optional[str]
    lp_preview_url: Optional[str]
    lp_image_urls: Dict
    ad_image_urls: Dict
    ad_copy: Dict
    ota_text: Dict = {}  # OTAテキスト（じゃらん、楽天トラベル向け）
    generation_prompts: Dict
    lp_revision_history: List = []  # LP修正履歴（最大10件）
    created_at: datetime

    class Config:
        from_attributes = True


