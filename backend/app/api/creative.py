from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Dict, Tuple
from pydantic import BaseModel
import os
import uuid
import re
import mimetypes

from app.core.database import get_session
from app.core.llm import get_llm_client
from app.core.s3_client import get_s3_client
from app.core.config import settings
from app.models import MarketingPlan, CreativeAsset, AnalysisSession, FacilityAdminHotel, Hotel
from app.schemas.creative import (
    CreativeGenerationRequest,
    CreativeAssetResponse
)
from app.services.creative_generator import CreativeGenerator
from app.auth.dependencies import require_hotel_access, require_hotel_editor

router = APIRouter(prefix="/api/creative", tags=["creative"])

AD_IMAGE_SLOTS = ("display_wide", "display_square", "display_vertical")
AD_IMAGE_TYPE_PREFERENCES = {
    "display_wide": ("exterior", "lobby", "interior", "sightseeing", "other"),
    "display_square": ("room", "bath", "cuisine", "restaurant", "interior", "other"),
    "display_vertical": ("bath", "room", "interior", "sightseeing", "other"),
}

# LP 画像スロットと割り当て優先 type の順
_LP_IMAGE_SLOT_PREFERENCES: Dict[str, Tuple] = {
    "hero":        ("exterior", "lobby", "interior", "other"),
    "feature1":    ("room", "interior", "other"),
    "feature2":    ("bath", "room", "other"),
    "feature3":    ("cuisine", "restaurant", "other"),
    "surrounding": ("sightseeing", "exterior", "other"),
    "ambiance":    ("interior", "other", "exterior"),
}


def _map_facility_images_for_lp(hotel: Hotel) -> Dict[str, str]:
    """
    施設画像（facility_images）を LP 用スロットにマッピングして返す。

    各スロットに type の優先順で未使用画像を割り当てる。
    有効な画像（/static/hotel_images/ から始まる URL）のみを対象とし、
    1枚の画像を複数スロットに重複使用しない。

    Returns:
        {slot_name: url} の辞書。有効な画像が 0 件なら空辞書を返す。
    """
    images = hotel.facility_images or []
    valid_images = [
        item for item in images
        if isinstance(item, dict)
        and isinstance(item.get("url"), str)
        and item["url"].startswith("/static/hotel_images/")
    ]
    if not valid_images:
        return {}

    valid_images.sort(key=lambda x: (x.get("order", 9999), str(x.get("key", ""))))

    used_keys: set = set()
    result: Dict[str, str] = {}

    for slot, preferences in _LP_IMAGE_SLOT_PREFERENCES.items():
        chosen = None
        for preferred_type in preferences:
            for item in valid_images:
                if item.get("type") != preferred_type:
                    continue
                if item.get("key") in used_keys:
                    continue
                chosen = item
                break
            if chosen:
                break

        # 優先 type で見つからなければ未使用の先頭画像を使う
        if not chosen:
            for item in valid_images:
                if item.get("key") not in used_keys:
                    chosen = item
                    break

        if chosen:
            result[slot] = chosen["url"]
            if chosen.get("key"):
                used_keys.add(chosen["key"])

    return result


def _select_ad_reference_images(hotel: Hotel) -> Tuple[Dict[str, dict], str]:
    """施設画像（S3配信URL）を広告枠ごとの参照画像として選定する。"""
    images = hotel.facility_images or []
    valid_images = []
    for item in images:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if isinstance(url, str) and url.startswith("/static/hotel_images/"):
            valid_images.append(item)

    if not valid_images:
        return {}, "施設画像が未登録のため、S3画像を広告枠に割り当てできませんでした。"

    valid_images.sort(key=lambda x: (x.get("order", 9999), str(x.get("key", ""))))

    selected: Dict[str, dict] = {}
    used_keys = set()

    for slot in AD_IMAGE_SLOTS:
        preferences = AD_IMAGE_TYPE_PREFERENCES.get(slot, ())
        chosen = None
        for preferred_type in preferences:
            for item in valid_images:
                if item.get("type") != preferred_type:
                    continue
                key = item.get("key")
                if key in used_keys:
                    continue
                chosen = item
                break
            if chosen:
                break

        if not chosen:
            for item in valid_images:
                key = item.get("key")
                if key in used_keys:
                    continue
                chosen = item
                break

        if chosen:
            selected[slot] = {
                "url": chosen.get("url"),
                "type": chosen.get("type"),
                "description": chosen.get("description", ""),
                "key": chosen.get("key"),
            }
            if chosen.get("key"):
                used_keys.add(chosen["key"])

    summary_lines = [
        "【広告画像ソース】",
        "S3上の施設画像（/static/hotel_images/...）を使用しました。",
    ]
    for slot in AD_IMAGE_SLOTS:
        if slot in selected:
            summary_lines.append(f"- {slot}: {selected[slot].get('url')}")

    return selected, "\n".join(summary_lines)


def _fetch_s3_image_bytes(hotel_id: int, image_url: str) -> Tuple[bytes, str]:
    """施設画像URLからS3オブジェクトを取得して (bytes, mime_type) を返す。"""
    if not image_url or not image_url.startswith(f"/static/hotel_images/{hotel_id}/"):
        raise ValueError(f"施設画像URL形式が不正です: {image_url}")

    filename = image_url.split("/")[-1]
    s3_key = f"hotel_images/{hotel_id}/{filename}"

    client = get_s3_client()
    resp = client.get_object(Bucket=settings.S3_BUCKET, Key=s3_key)
    body = resp["Body"].read()
    mime_type = resp.get("ContentType") or mimetypes.guess_type(filename)[0] or "image/webp"
    return body, mime_type


class CreativeGenerationRequestAuth(BaseModel):
    """認証付きクリエイティブ生成リクエスト"""
    plan_id: int
    generate_lp: bool = True
    generate_images: bool = True
    generate_ad_copy: bool = True
    generate_ota_text: bool = False  # OTAテキスト（じゃらん、楽天トラベル向け）


class SNSPostGenerationRequest(BaseModel):
    """SNS投稿生成リクエスト"""
    platform: str  # "instagram", "facebook", "twitter"
    post_type: str  # "温泉紹介", "料理紹介", "イベント告知", "その他"
    description: str = ""  # どんな投稿を作りたいかの説明


class SNSPostResponse(BaseModel):
    """SNS投稿生成レスポンス"""
    platform: str
    post_type: str
    content: str
    hashtags: list[str]
    generated_at: str


# ============================================
# 施設認証付きエンドポイント（マルチテナント対応）
# ============================================

@router.post("/hotels/{hotel_id}/generate", response_model=CreativeAssetResponse)
async def generate_creative_assets_authenticated(
    hotel_id: int,
    request: CreativeGenerationRequestAuth,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    クリエイティブアセットを生成（認証付き）
    
    - LP（ランディングページ）のコード生成
    - 広告画像生成用プロンプト作成
    - 広告コピー生成
    """
    # 施設の分析セッションを取得して検証
    analysis_statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(analysis_statement).first()
    
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    # 施設情報を取得（CV URL用）
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="施設が見つかりません")
    
    # マーケティングプランの存在確認と権限チェック
    marketing_plan = session.get(MarketingPlan, request.plan_id)
    if not marketing_plan:
        raise HTTPException(status_code=404, detail="マーケティングプランが見つかりません")
    
    if marketing_plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=403, detail="このプランへのアクセス権限がありません")
    
    # LP生成時はCV URLが必須
    if request.generate_lp and not hotel.cv_url:
        raise HTTPException(
            status_code=400, 
            detail="LP生成にはCV用URLの設定が必要です。施設設定でCV用URLを登録してください。"
        )
    
    try:
        generator = CreativeGenerator()
        llm_client = get_llm_client()
        # LP生成用（gemini-3-pro-preview）
        llm_client_lp = get_llm_client(model_name="gemini-3-pro-preview")
        # 画像生成用（gemini-3-pro-image-preview）
        llm_client_image = get_llm_client(model_name="gemini-3-pro-image-preview")
        
        lp_code = None
        lp_prompt = None
        lp_image_urls = {}
        lp_image_gen_prompt = None
        ad_image_urls = {}
        ad_image_gen_prompt = None
        ad_copy = {}
        ad_copy_prompt = None
        ota_text = {}
        ota_text_prompt = None
        
        # LP用画像: 施設登録済み画像を優先して転用し、未登録の場合のみ AI 生成
        if request.generate_lp:
            mapped = _map_facility_images_for_lp(hotel)
            if mapped:
                lp_image_urls = mapped
                lp_image_gen_prompt = (
                    "【LP画像】施設画像（facility_images）をスロットにマッピングして使用しました。\n"
                    + "\n".join(f"- {slot}: {url}" for slot, url in mapped.items())
                )
            else:
                # 施設画像未登録の場合のみ AI 生成にフォールバック
                lp_image_urls, lp_image_gen_prompt = await generator.generate_lp_images(
                    marketing_plan=marketing_plan,
                    llm_client=llm_client_image,
                    hotel_id=hotel_id
                )

        # 広告用画像を生成
        if request.generate_images:
            selected_refs, selection_log = _select_ad_reference_images(hotel)
            if not selected_refs:
                raise HTTPException(
                    status_code=400,
                    detail="広告画像生成には施設画像が必要です。施設設定で画像を登録してください。"
                )
            reference_payload = {}
            try:
                for slot, ref in selected_refs.items():
                    image_data, mime_type = _fetch_s3_image_bytes(hotel_id, ref.get("url", ""))
                    reference_payload[slot] = {
                        "data": image_data,
                        "mime_type": mime_type,
                        "url": ref.get("url", ""),
                    }
            except Exception:
                raise HTTPException(
                    status_code=503,
                    detail="施設画像の取得に失敗しました。ストレージ接続を確認してください。"
                )

            ad_image_urls, generation_log = await generator.generate_ad_images_with_references(
                marketing_plan=marketing_plan,
                llm_client=llm_client_image,
                hotel_id=hotel_id,
                reference_images=reference_payload,
                hotel_info={"name": hotel.name, "address": hotel.address or ""},
            )
            ad_image_gen_prompt = f"{selection_log}\n\n{generation_log}"
        
        # LP生成（LP用画像URLとホテル情報を渡す）
        if request.generate_lp:
            # 有効な静的URLのみを抽出（エラー情報・不正値を除外）
            valid_lp_image_urls = {
                key: value
                for key, value in lp_image_urls.items()
                if isinstance(value, str) and value.startswith("/static/")
            }

            lp_code, lp_prompt = await generator.generate_landing_page(
                marketing_plan=marketing_plan,
                llm_client=llm_client_lp,
                cv_url=hotel.cv_url,
                hotel_info={
                    "name": hotel.name,
                    "address": hotel.address,
                    "phone": hotel.phone,
                    "website": hotel.website,
                },
                image_urls=valid_lp_image_urls
            )
        
        # 広告コピー生成
        if request.generate_ad_copy:
            ad_copy, ad_copy_prompt = await generator.generate_ad_copy(
                marketing_plan=marketing_plan,
                llm_client=llm_client
            )
        
        # OTAテキスト生成（じゃらん、楽天トラベル向け）
        if request.generate_ota_text:
            ota_text, ota_text_prompt = await generator.generate_ota_text(
                marketing_plan=marketing_plan,
                llm_client=llm_client,
                hotel_info={
                    "name": hotel.name,
                    "address": hotel.address,
                }
            )
        
        # 既存のアセットがあるか確認
        statement = select(CreativeAsset).where(
            CreativeAsset.marketing_plan_id == request.plan_id
        )
        existing_asset = session.exec(statement).first()
        
        generation_prompts = {
            "lp_prompt": lp_prompt,
            "lp_image_generation_prompt": lp_image_gen_prompt,
            "ad_image_generation_prompt": ad_image_gen_prompt,
            "ad_copy_prompt": ad_copy_prompt,
            "ota_text_prompt": ota_text_prompt
        }
        
        if existing_asset:
            if lp_code:
                existing_asset.lp_source_code = lp_code
            if lp_image_urls:
                existing_asset.lp_image_urls = lp_image_urls
            if ad_image_urls:
                existing_asset.ad_image_urls = ad_image_urls
            if ad_copy:
                existing_asset.ad_copy = ad_copy
            if ota_text:
                existing_asset.ota_text = ota_text
            existing_asset.generation_prompts = generation_prompts
            creative_asset = existing_asset
        else:
            creative_asset = CreativeAsset(
                marketing_plan_id=request.plan_id,
                lp_source_code=lp_code,
                lp_image_urls=lp_image_urls,
                ad_image_urls=ad_image_urls,
                ad_copy=ad_copy,
                ota_text=ota_text,
                generation_prompts=generation_prompts
            )
            session.add(creative_asset)
        
        session.commit()
        session.refresh(creative_asset)
        
        # LPが生成されている場合はファイルとして保存
        if lp_code and creative_asset.id:
            # LP用画像のみを抽出してプレビュー用に渡す
            valid_lp_images = {}
            for key, value in lp_image_urls.items():
                if isinstance(value, str) and value.startswith("/static/"):
                    valid_lp_images[key] = value
            
            preview_url = generator.save_lp_to_file(
                lp_source_code=lp_code,
                hotel_id=hotel_id,
                asset_id=creative_asset.id,
                image_urls=valid_lp_images if valid_lp_images else None
            )
            creative_asset.lp_preview_url = preview_url
            session.commit()
            session.refresh(creative_asset)
        
        return creative_asset
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"クリエイティブ生成エラー: {str(e)}")


@router.get("/hotels/{hotel_id}/plans/{plan_id}/assets", response_model=List[CreativeAssetResponse])
async def list_assets_by_hotel_plan(
    hotel_id: int,
    plan_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """施設のプランに紐づくクリエイティブアセット一覧を取得（認証付き）"""
    # 施設の分析セッションを取得して検証
    analysis_statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(analysis_statement).first()
    
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    # マーケティングプランの権限チェック
    marketing_plan = session.get(MarketingPlan, plan_id)
    if not marketing_plan or marketing_plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    statement = select(CreativeAsset).where(CreativeAsset.marketing_plan_id == plan_id)
    assets = session.exec(statement).all()
    return assets


@router.post("/hotels/{hotel_id}/assets/{asset_id}/save-lp")
async def save_lp_to_file(
    hotel_id: int,
    asset_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    既存アセットのLPをファイルとして保存（認証付き）
    
    - LPソースコードをHTMLファイルとして保存
    - 画像パスを相対パスに変換
    - プレビューURLを返却
    """
    # 施設の分析セッションを取得して検証
    analysis_statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(analysis_statement).first()
    
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    asset = session.get(CreativeAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="クリエイティブアセットが見つかりません")
    
    # プランの権限チェック
    marketing_plan = session.get(MarketingPlan, asset.marketing_plan_id)
    if not marketing_plan or marketing_plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=403, detail="このアセットへのアクセス権限がありません")
    
    if not asset.lp_source_code:
        raise HTTPException(status_code=400, detail="LPソースコードがありません")
    
    try:
        generator = CreativeGenerator()
        
        # 画像URLを取得（エラー情報を含まない実際の画像パスのみ）
        image_urls = {}
        if asset.lp_image_urls:
            for key, value in asset.lp_image_urls.items():
                if isinstance(value, str) and value.startswith("/static/"):
                    image_urls[key] = value
        
        preview_url = generator.save_lp_to_file(
            lp_source_code=asset.lp_source_code,
            hotel_id=hotel_id,
            asset_id=asset_id,
            image_urls=image_urls if image_urls else None
        )
        
        asset.lp_preview_url = preview_url
        session.commit()
        session.refresh(asset)
        
        return {
            "message": "LPを保存しました",
            "preview_url": preview_url,
            "asset_id": asset_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LP保存エラー: {str(e)}")


@router.delete("/hotels/{hotel_id}/assets/{asset_id}")
async def delete_creative_asset_authenticated(
    hotel_id: int,
    asset_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """クリエイティブアセットを削除（認証付き、編集者以上）"""
    # 施設の分析セッションを取得して検証
    analysis_statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(analysis_statement).first()
    
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    asset = session.get(CreativeAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="クリエイティブアセットが見つかりません")
    
    # プランの権限チェック
    marketing_plan = session.get(MarketingPlan, asset.marketing_plan_id)
    if not marketing_plan or marketing_plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=403, detail="このアセットへのアクセス権限がありません")
    
    session.delete(asset)
    session.commit()
    
    return {"message": "クリエイティブアセットを削除しました", "asset_id": asset_id}


# ============================================
# 既存エンドポイント（後方互換性のため保持）
# ============================================


@router.post("/generate", response_model=CreativeAssetResponse)
async def generate_creative_assets(
    request: CreativeGenerationRequest,
    session: Session = Depends(get_session)
):
    """
    クリエイティブアセットを生成
    
    - LP（ランディングページ）のコード生成
    - 広告画像生成用プロンプト作成
    - 広告コピー生成
    """
    # マーケティングプランの存在確認
    marketing_plan = session.get(MarketingPlan, request.marketing_plan_id)
    if not marketing_plan:
        raise HTTPException(status_code=404, detail="マーケティングプランが見つかりません")

    hotel = None
    if marketing_plan.analysis_session_id:
        analysis_session = session.get(AnalysisSession, marketing_plan.analysis_session_id)
        if analysis_session:
            hotel = session.get(Hotel, analysis_session.hotel_id)
    
    try:
        generator = CreativeGenerator()
        llm_client = get_llm_client()
        llm_client_image = get_llm_client(model_name="gemini-3-pro-image-preview")
        
        lp_code = None
        lp_prompt = None
        image_prompts = {}
        image_gen_prompt = None
        ad_copy = {}
        ad_copy_prompt = None
        
        # LP生成
        if request.generate_lp:
            lp_code, lp_prompt = await generator.generate_landing_page(
                marketing_plan=marketing_plan,
                llm_client=llm_client
            )
        
        # 画像プロンプト生成
        if request.generate_images:
            if not hotel:
                raise HTTPException(
                    status_code=400,
                    detail="広告画像生成に必要な施設情報が見つかりません"
                )
            selected_refs, selection_log = _select_ad_reference_images(hotel)
            if not selected_refs:
                raise HTTPException(
                    status_code=400,
                    detail="広告画像生成には施設画像が必要です。施設設定で画像を登録してください。"
                )
            reference_payload = {}
            try:
                for slot, ref in selected_refs.items():
                    image_data, mime_type = _fetch_s3_image_bytes(hotel.id, ref.get("url", ""))
                    reference_payload[slot] = {
                        "data": image_data,
                        "mime_type": mime_type,
                        "url": ref.get("url", ""),
                    }
            except Exception:
                raise HTTPException(
                    status_code=503,
                    detail="施設画像の取得に失敗しました。ストレージ接続を確認してください。"
                )

            image_prompts, generation_log = await generator.generate_ad_images_with_references(
                marketing_plan=marketing_plan,
                llm_client=llm_client_image,
                hotel_id=hotel.id,
                reference_images=reference_payload,
                hotel_info={"name": hotel.name, "address": hotel.address or ""} if hotel else None,
            )
            image_gen_prompt = f"{selection_log}\n\n{generation_log}"
        
        # 広告コピー生成
        if request.generate_ad_copy:
            ad_copy, ad_copy_prompt = await generator.generate_ad_copy(
                marketing_plan=marketing_plan,
                llm_client=llm_client
            )
        
        # 既存のアセットがあるか確認
        statement = select(CreativeAsset).where(
            CreativeAsset.marketing_plan_id == request.marketing_plan_id
        )
        existing_asset = session.exec(statement).first()
        
        generation_prompts = {
            "lp_prompt": lp_prompt,
            "image_generation_prompt": image_gen_prompt,
            "ad_copy_prompt": ad_copy_prompt
        }
        
        if existing_asset:
            # 既存アセットを更新
            if lp_code:
                existing_asset.lp_source_code = lp_code
            if image_prompts:
                existing_asset.ad_image_urls = image_prompts
            if ad_copy:
                existing_asset.ad_copy = ad_copy
            existing_asset.generation_prompts = generation_prompts
            creative_asset = existing_asset
        else:
            # 新規アセットを作成
            creative_asset = CreativeAsset(
                marketing_plan_id=request.marketing_plan_id,
                lp_source_code=lp_code,
                ad_image_urls=image_prompts,
                ad_copy=ad_copy,
                generation_prompts=generation_prompts
            )
            session.add(creative_asset)
        
        session.commit()
        session.refresh(creative_asset)
        
        # LPが生成されている場合はファイルとして保存
        # 注: このエンドポイントはhotel_idを受け取らないため、プランから取得
        if lp_code and creative_asset.id:
            # プランからホテルIDを取得
            analysis_session = session.get(AnalysisSession, marketing_plan.analysis_session_id)
            if analysis_session:
                preview_url = generator.save_lp_to_file(
                    lp_source_code=lp_code,
                    hotel_id=analysis_session.hotel_id,
                    asset_id=creative_asset.id,
                    image_urls=image_prompts if isinstance(image_prompts, dict) else None
                )
                creative_asset.lp_preview_url = preview_url
                session.commit()
                session.refresh(creative_asset)
        
        return creative_asset
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"クリエイティブ生成エラー: {str(e)}")


@router.get("/assets/{asset_id}", response_model=CreativeAssetResponse)
async def get_creative_asset(
    asset_id: int,
    session: Session = Depends(get_session)
):
    """クリエイティブアセットの詳細を取得"""
    asset = session.get(CreativeAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="クリエイティブアセットが見つかりません")
    return asset


@router.get("/plans/{plan_id}/assets", response_model=List[CreativeAssetResponse])
async def list_assets_by_plan(
    plan_id: int,
    session: Session = Depends(get_session)
):
    """特定のプランに紐づくクリエイティブアセット一覧を取得"""
    statement = select(CreativeAsset).where(CreativeAsset.marketing_plan_id == plan_id)
    assets = session.exec(statement).all()
    return assets


@router.delete("/assets/{asset_id}")
async def delete_creative_asset(
    asset_id: int,
    session: Session = Depends(get_session)
):
    """クリエイティブアセットを削除"""
    asset = session.get(CreativeAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="クリエイティブアセットが見つかりません")
    
    session.delete(asset)
    session.commit()
    
    return {"message": "クリエイティブアセットを削除しました", "asset_id": asset_id}


@router.post("/hotels/{hotel_id}/generate-sns-post", response_model=SNSPostResponse)
async def generate_sns_post(
    hotel_id: int,
    request: SNSPostGenerationRequest,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    SNS投稿を生成
    
    - プラットフォーム（Instagram、Facebook、Twitter）に最適化された投稿を生成
    - 投稿タイプに応じたコンテンツを作成
    - 説明欄の内容を反映した投稿を生成
    """
    from datetime import datetime
    
    # 施設情報を取得
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="施設が見つかりません")
    
    # 分析セッションを取得
    analysis_statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(analysis_statement).first()
    
    # マーケティングプランがあれば取得
    marketing_plan = None
    if analysis_session:
        plan_statement = select(MarketingPlan).where(
            MarketingPlan.analysis_session_id == analysis_session.id,
            MarketingPlan.status == "approved"
        )
        marketing_plan = session.exec(plan_statement).first()
    
    try:
        llm_client = get_llm_client()
        
        # プラットフォームに応じた文字数制限とスタイル
        platform_configs = {
            "instagram": {
                "max_chars": 2200,
                "hashtag_count": "10〜15個",
                "style": "視覚的な描写を重視し、改行を活用した読みやすいレイアウト"
            },
            "facebook": {
                "max_chars": 500,
                "hashtag_count": "3〜5個",
                "style": "詳細な情報を含み、親しみやすいトーンで"
            },
            "twitter": {
                "max_chars": 280,
                "hashtag_count": "2〜3個",
                "style": "簡潔で印象的、ハッシュタグ込みで140文字以内が理想"
            }
        }
        
        platform_config = platform_configs.get(request.platform.lower(), platform_configs["instagram"])
        
        # プロンプトを作成
        plan_info = ""
        if marketing_plan:
            plan_info = f"""
【マーケティングプラン情報】
コンセプト: {marketing_plan.concept}
ターゲット: {marketing_plan.target_audience}
"""
        
        description_info = ""
        if request.description.strip():
            description_info = f"""
【ユーザーからの要望】
{request.description}

上記の要望を必ず投稿内容に反映させてください。
"""
        
        prompt = f"""以下の条件でSNS投稿を作成してください。

【施設情報】
施設名: {hotel.name}
住所: {hotel.address}
{plan_info}
【投稿条件】
プラットフォーム: {request.platform}
投稿タイプ: {request.post_type}
文字数制限: {platform_config['max_chars']}文字以内
ハッシュタグ: {platform_config['hashtag_count']}
スタイル: {platform_config['style']}
{description_info}
【出力形式】
以下のJSON形式で出力してください：
{{
    "content": "投稿本文（ハッシュタグは含めない）",
    "hashtags": ["#ハッシュタグ1", "#ハッシュタグ2", ...]
}}

{request.post_type}に関する魅力的な投稿を作成してください。
施設の特徴や魅力を活かし、{request.platform}ユーザーの興味を引く内容にしてください。
"""
        
        system_prompt = """あなたは宿泊業界のSNSマーケティング専門家です。
各プラットフォームの特性を理解し、エンゲージメントを最大化する投稿を作成してください。

重要なポイント：
- 施設の魅力を具体的に伝える
- 感情を動かす表現を使う
- 行動を促す言葉を入れる
- 季節感や限定感を演出
- 絵文字を効果的に使用"""

        response = await llm_client.generate_structured_output(
            user_prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=1000
        )
        
        # レスポンスをパース
        import json
        import re
        
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response)
        
        return SNSPostResponse(
            platform=request.platform,
            post_type=request.post_type,
            content=result.get("content", ""),
            hashtags=result.get("hashtags", []),
            generated_at=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SNS投稿生成エラー: {str(e)}")


@router.post("/hotels/{hotel_id}/assets/{asset_id}/lp-images/{image_type}")
async def upload_lp_image(
    hotel_id: int,
    asset_id: int,
    image_type: str,
    file: UploadFile = File(...),
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    LP用画像をアップロードして差し替え
    
    - image_type: hero, feature, ambiance のいずれか
    - 古い画像を新しい画像で置き換え
    - HTMLファイル内の画像パスも更新
    - DB内のlp_source_codeも更新
    """
    # アセットの存在確認
    asset = session.get(CreativeAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="クリエイティブアセットが見つかりません")
    
    # 画像タイプの検証
    valid_types = ["hero", "feature", "ambiance"]
    if image_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"無効な画像タイプです。有効な値: {', '.join(valid_types)}"
        )
    
    # ファイル形式の検証
    allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"無効なファイル形式です。有効な形式: {', '.join(allowed_extensions)}"
        )
    
    # LP画像ディレクトリ
    lp_dir = os.path.join("static", "lp", str(hotel_id))
    os.makedirs(lp_dir, exist_ok=True)
    
    # 現在のLP画像URLを取得（新しい辞書を作成してSQLAlchemyが変更を検出できるようにする）
    lp_image_urls = dict(asset.lp_image_urls) if asset.lp_image_urls else {}
    old_image_path = lp_image_urls.get(image_type, "")
    old_filename = old_image_path.split("/")[-1] if old_image_path else None
    
    # 新しいファイル名を生成
    new_filename = f"{image_type}_{uuid.uuid4().hex[:8]}{file_ext}"
    new_filepath = os.path.join(lp_dir, new_filename)
    
    # ファイルを保存
    content = await file.read()
    with open(new_filepath, "wb") as f:
        f.write(content)
    
    # 古いファイルを削除
    if old_filename:
        old_filepath = os.path.join(lp_dir, old_filename)
        if os.path.exists(old_filepath):
            try:
                os.remove(old_filepath)
            except Exception as e:
                print(f"古い画像の削除に失敗: {e}")
    
    # 新しい画像URLを設定
    new_image_url = f"/static/lp/{hotel_id}/{new_filename}"
    lp_image_urls[image_type] = new_image_url
    asset.lp_image_urls = lp_image_urls
    
    # 画像パス置換用のヘルパー関数
    def replace_image_path(content: str, old_name: str | None, new_name: str) -> str:
        """HTMLコンテンツ内の画像パスを置換"""
        if old_name:
            # 古いファイル名を新しいファイル名に置換（相対パス形式）
            content = content.replace(f"./{old_name}", f"./{new_name}")
            content = content.replace(f'"{old_name}"', f'"./{new_name}"')
            content = content.replace(f"'{old_name}'", f"'./{new_name}'")
            # 絶対パス形式も対応
            content = content.replace(f"/static/lp/{hotel_id}/{old_name}", f"./{new_name}")
        
        # 画像タイプに基づいた正規表現パターンでも置換（より確実な置換）
        # hero_XXXXXXXX.jpg, feature_XXXXXXXX.png などのパターンに対応
        pattern = rf"\./{image_type}_[a-f0-9]+\.(jpg|jpeg|png|webp)"
        content = re.sub(pattern, f"./{new_name}", content)
        
        # url('...') パターンにも対応
        pattern_url = rf"url\(['\"]?\./{image_type}_[a-f0-9]+\.(jpg|jpeg|png|webp)['\"]?\)"
        content = re.sub(pattern_url, f"url('./{new_name}')", content)
        
        return content
    
    # DB内のlp_source_codeを更新
    if asset.lp_source_code:
        try:
            updated_source = replace_image_path(asset.lp_source_code, old_filename, new_filename)
            asset.lp_source_code = updated_source
            print(f"lp_source_code更新: {image_type}画像パスを {new_filename} に変更")
        except Exception as e:
            print(f"lp_source_codeの更新に失敗: {e}")
    
    # 辞書型フィールドの変更をSQLAlchemyに明示的に通知
    # これがないと、辞書の内部変更が検出されずDBに保存されない
    flag_modified(asset, "lp_image_urls")
    
    # HTMLファイル内の画像パスを更新
    if asset.lp_preview_url:
        html_filepath = os.path.join("static", "lp", str(hotel_id), f"lp_{asset_id}.html")
        if os.path.exists(html_filepath):
            try:
                with open(html_filepath, "r", encoding="utf-8") as f:
                    html_content = f.read()
                
                html_content = replace_image_path(html_content, old_filename, new_filename)
                
                with open(html_filepath, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                print(f"HTMLファイル更新: {html_filepath}")
                    
            except Exception as e:
                print(f"HTMLファイルの更新に失敗: {e}")
        else:
            print(f"HTMLファイルが見つかりません: {html_filepath}")
    
    # 更新日時を更新
    from datetime import datetime
    asset.updated_at = datetime.utcnow()
    
    session.commit()
    session.refresh(asset)
    
    print(f"DB更新完了: asset_id={asset_id}, lp_image_urls={asset.lp_image_urls}")
    
    return {
        "message": f"{image_type}画像をアップロードしました",
        "image_type": image_type,
        "new_url": new_image_url,
        "filename": new_filename,
        "lp_image_urls": asset.lp_image_urls  # refreshした後の値を返す
    }
