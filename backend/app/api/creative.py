from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from pydantic import BaseModel

from app.core.database import get_session
from app.core.llm import get_llm_client
from app.models import MarketingPlan, CreativeAsset, AnalysisSession, FacilityAdminHotel
from app.schemas.creative import (
    CreativeGenerationRequest,
    CreativeAssetResponse
)
from app.services.creative_generator import CreativeGenerator
from app.auth.dependencies import require_hotel_access, require_hotel_editor

router = APIRouter(prefix="/api/creative", tags=["creative"])


class CreativeGenerationRequestAuth(BaseModel):
    """認証付きクリエイティブ生成リクエスト"""
    plan_id: int
    generate_lp: bool = True
    generate_images: bool = True
    generate_ad_copy: bool = True


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
    
    # マーケティングプランの存在確認と権限チェック
    marketing_plan = session.get(MarketingPlan, request.plan_id)
    if not marketing_plan:
        raise HTTPException(status_code=404, detail="マーケティングプランが見つかりません")
    
    if marketing_plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=403, detail="このプランへのアクセス権限がありません")
    
    try:
        generator = CreativeGenerator()
        llm_client = get_llm_client()
        
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
            image_prompts, image_gen_prompt = await generator.generate_ad_images(
                marketing_plan=marketing_plan,
                llm_client=llm_client
            )
        
        # 広告コピー生成
        if request.generate_ad_copy:
            ad_copy, ad_copy_prompt = await generator.generate_ad_copy(
                marketing_plan=marketing_plan,
                llm_client=llm_client
            )
        
        # 既存のアセットがあるか確認
        statement = select(CreativeAsset).where(
            CreativeAsset.marketing_plan_id == request.plan_id
        )
        existing_asset = session.exec(statement).first()
        
        generation_prompts = {
            "lp_prompt": lp_prompt,
            "image_generation_prompt": image_gen_prompt,
            "ad_copy_prompt": ad_copy_prompt
        }
        
        if existing_asset:
            if lp_code:
                existing_asset.lp_source_code = lp_code
            if image_prompts:
                existing_asset.ad_image_urls = image_prompts
            if ad_copy:
                existing_asset.ad_copy = ad_copy
            existing_asset.generation_prompts = generation_prompts
            creative_asset = existing_asset
        else:
            creative_asset = CreativeAsset(
                marketing_plan_id=request.plan_id,
                lp_source_code=lp_code,
                ad_image_urls=image_prompts,
                ad_copy=ad_copy,
                generation_prompts=generation_prompts
            )
            session.add(creative_asset)
        
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
    
    try:
        generator = CreativeGenerator()
        llm_client = get_llm_client()
        
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
            image_prompts, image_gen_prompt = await generator.generate_ad_images(
                marketing_plan=marketing_plan,
                llm_client=llm_client
            )
        
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


