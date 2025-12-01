from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.core.database import get_session
from app.core.llm import get_llm_client
from app.models import MarketingPlan, CreativeAsset
from app.schemas.creative import (
    CreativeGenerationRequest,
    CreativeAssetResponse
)
from app.services.creative_generator import CreativeGenerator

router = APIRouter(prefix="/api/creative", tags=["creative"])


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


