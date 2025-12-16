from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from typing import List

from app.core.database import get_session
from app.core.llm import get_llm_client
from app.models import Hotel, AnalysisSession, FacilityAdmin, FacilityAdminHotel
from app.schemas.analysis import (
    HotelCreate,
    HotelResponse,
    CSVAnalysisResponse,
    MarketResearchRequest,
    MarketResearchResponse
)
from app.services.csv_analyzer import CSVAnalyzer
from app.services.analysis_service import AnalysisService
from app.auth.dependencies import get_current_facility_admin, require_hotel_access

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


# ============================================
# 施設認証付きエンドポイント（マルチテナント対応）
# ============================================

@router.post("/hotels/{hotel_id}/customer", response_model=CSVAnalysisResponse)
async def analyze_customer_data_authenticated(
    hotel_id: int,
    file: UploadFile = File(...),
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    顧客データ（CSV）を分析（認証付き）
    
    - CSVファイルをアップロード
    - スキーマを自動推定
    - 統計情報を計算
    - AIによるインサイトを生成
    """
    # 宿泊施設の存在確認
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    # ファイルタイプの確認
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSVファイルをアップロードしてください")
    
    try:
        # ファイルを読み込み
        file_content = await file.read()
        
        # CSV分析サービスを初期化
        analyzer = CSVAnalyzer()
        llm_client = get_llm_client(model_name="gemini-2.5-flash-lite")
        
        # 分析実行
        statistics, insights = await analyzer.analyze_csv(file_content, llm_client)
        
        # 分析セッションを作成または更新
        statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
        existing_session = session.exec(statement).first()
        
        if existing_session:
            existing_session.csv_statistics = statistics
            existing_session.csv_insights = insights
            analysis_session = existing_session
        else:
            analysis_session = AnalysisSession(
                hotel_id=hotel_id,
                csv_statistics=statistics,
                csv_insights=insights
            )
            session.add(analysis_session)
        
        session.commit()
        session.refresh(analysis_session)
        
        return CSVAnalysisResponse(
            session_id=analysis_session.id,
            statistics=statistics,
            insights=insights,
            created_at=analysis_session.created_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析エラー: {str(e)}")


@router.post("/hotels/{hotel_id}/upload-csv", response_model=CSVAnalysisResponse)
async def upload_and_analyze_csv_authenticated(
    hotel_id: int,
    file: UploadFile = File(...),
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    顧客データ（CSV）を分析（Gemini 2.5 Flash-Lite版、認証付き）
    
    - CSVファイルをアップロード
    - エンコーディング自動判別
    - AIによるスキーマ推定
    - 統計情報を計算
    - AIマーケティングインサイトを生成
    """
    # 宿泊施設の存在確認
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    # ファイルタイプの確認
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSVファイルをアップロードしてください")
    
    try:
        # ファイルを読み込み
        file_content = await file.read()
        
        # 新しいAnalysisServiceを使用
        analysis_service = AnalysisService()
        
        # 分析実行
        statistics, insights = await analysis_service.analyze_csv(file_content)
        
        # 分析セッションを作成または更新
        statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
        existing_session = session.exec(statement).first()
        
        if existing_session:
            existing_session.csv_statistics = statistics
            existing_session.csv_insights = insights
            analysis_session = existing_session
        else:
            analysis_session = AnalysisSession(
                hotel_id=hotel_id,
                csv_statistics=statistics,
                csv_insights=insights
            )
            session.add(analysis_session)
        
        session.commit()
        session.refresh(analysis_session)
        
        return CSVAnalysisResponse(
            session_id=analysis_session.id,
            statistics=statistics,
            insights=insights,
            created_at=analysis_session.created_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析エラー: {str(e)}")


@router.post("/hotels/{hotel_id}/market", response_model=MarketResearchResponse)
async def analyze_market_authenticated(
    hotel_id: int,
    radius_km: float = 10.0,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    市場調査を実行（認証付き）
    
    - 競合施設のリサーチ
    - 口コミ分析
    - 地域トレンド分析
    """
    # 宿泊施設の存在確認
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    try:
        llm_client = get_llm_client()
        
        # 競合リサーチ
        competitors_data = await _research_competitors(hotel.address, radius_km, llm_client)
        
        # 口コミ要約
        reviews_summary = await _analyze_reviews(hotel.address, llm_client)
        
        # 地域トレンド分析
        regional_trends = await _analyze_regional_trends(hotel.address, llm_client)
        
        # 分析セッションを更新
        statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
        analysis_session = session.exec(statement).first()
        
        if analysis_session:
            analysis_session.competitors_list = competitors_data
            analysis_session.reviews_summary = reviews_summary
            analysis_session.regional_trends = regional_trends
        else:
            analysis_session = AnalysisSession(
                hotel_id=hotel_id,
                competitors_list=competitors_data,
                reviews_summary=reviews_summary,
                regional_trends=regional_trends
            )
            session.add(analysis_session)
        
        session.commit()
        session.refresh(analysis_session)
        
        return MarketResearchResponse(
            session_id=analysis_session.id,
            competitors=competitors_data,
            reviews_summary=reviews_summary,
            regional_trends=regional_trends,
            created_at=analysis_session.created_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"市場調査エラー: {str(e)}")


@router.get("/hotels/{hotel_id}/session")
async def get_analysis_session(
    hotel_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """施設の分析セッションを取得（認証付き）"""
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        return {"session_id": None, "message": "分析セッションがありません"}
    
    return {
        "session_id": analysis_session.id,
        "hotel_id": hotel_id,
        "csv_statistics": analysis_session.csv_statistics,
        "csv_insights": analysis_session.csv_insights,
        "competitors_list": analysis_session.competitors_list,
        "reviews_summary": analysis_session.reviews_summary,
        "regional_trends": analysis_session.regional_trends,
        "created_at": analysis_session.created_at,
        "updated_at": analysis_session.updated_at,
    }


# ============================================
# 既存エンドポイント（後方互換性のため保持）
# ============================================


@router.post("/hotels", response_model=HotelResponse)
async def create_hotel(
    hotel_data: HotelCreate,
    session: Session = Depends(get_session)
):
    """宿泊施設を登録"""
    hotel = Hotel(
        name=hotel_data.name,
        address=hotel_data.address,
        postal_code=hotel_data.postal_code,
        phone=hotel_data.phone,
        email=hotel_data.email,
        website=hotel_data.website,
        features=hotel_data.features or {},
        strengths=hotel_data.strengths or {}
    )
    
    session.add(hotel)
    session.commit()
    session.refresh(hotel)
    
    return hotel


@router.get("/hotels", response_model=List[HotelResponse])
async def list_hotels(session: Session = Depends(get_session)):
    """宿泊施設一覧を取得"""
    statement = select(Hotel)
    hotels = session.exec(statement).all()
    return hotels


@router.get("/hotels/{hotel_id}", response_model=HotelResponse)
async def get_hotel(
    hotel_id: int,
    session: Session = Depends(get_session)
):
    """宿泊施設の詳細を取得"""
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    return hotel


@router.post("/customer", response_model=CSVAnalysisResponse)
async def analyze_customer_data(
    hotel_id: int = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """
    顧客データ（CSV）を分析（従来の実装）
    
    - CSVファイルをアップロード
    - スキーマを自動推定
    - 統計情報を計算
    - AIによるインサイトを生成
    """
    # 宿泊施設の存在確認
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    # ファイルタイプの確認
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSVファイルをアップロードしてください")
    
    try:
        # ファイルを読み込み
        file_content = await file.read()
        
        # CSV分析サービスを初期化
        analyzer = CSVAnalyzer()
        llm_client = get_llm_client(model_name="gemini-2.5-flash-lite")
        
        # 分析実行
        statistics, insights = await analyzer.analyze_csv(file_content, llm_client)
        
        # 分析セッションを作成または更新
        # 既存のセッションがあるか確認
        statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
        existing_session = session.exec(statement).first()
        
        if existing_session:
            # 既存セッションを更新
            existing_session.csv_statistics = statistics
            existing_session.csv_insights = insights
            analysis_session = existing_session
        else:
            # 新規セッションを作成
            analysis_session = AnalysisSession(
                hotel_id=hotel_id,
                csv_statistics=statistics,
                csv_insights=insights
            )
            session.add(analysis_session)
        
        session.commit()
        session.refresh(analysis_session)
        
        return CSVAnalysisResponse(
            session_id=analysis_session.id,
            statistics=statistics,
            insights=insights,
            created_at=analysis_session.created_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析エラー: {str(e)}")


@router.post("/upload-csv", response_model=CSVAnalysisResponse)
async def upload_and_analyze_csv(
    hotel_id: int = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """
    顧客データ（CSV）を分析（Gemini 2.5 Flash-Lite版）
    
    - CSVファイルをアップロード
    - エンコーディング自動判別
    - AIによるスキーマ推定
    - 統計情報を計算
    - AIマーケティングインサイトを生成
    
    使用モデル: Gemini 2.5 Flash-Lite
    """
    # 宿泊施設の存在確認
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    # ファイルタイプの確認
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSVファイルをアップロードしてください")
    
    try:
        # ファイルを読み込み
        file_content = await file.read()
        
        # 新しいAnalysisServiceを使用
        analysis_service = AnalysisService()
        
        # 分析実行（スキーマ推定 → 計算 → インサイト生成）
        statistics, insights = await analysis_service.analyze_csv(file_content)
        
        # 分析セッションを作成または更新
        statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
        existing_session = session.exec(statement).first()
        
        if existing_session:
            # 既存セッションを更新
            existing_session.csv_statistics = statistics
            existing_session.csv_insights = insights
            analysis_session = existing_session
        else:
            # 新規セッションを作成
            analysis_session = AnalysisSession(
                hotel_id=hotel_id,
                csv_statistics=statistics,
                csv_insights=insights
            )
            session.add(analysis_session)
        
        session.commit()
        session.refresh(analysis_session)
        
        return CSVAnalysisResponse(
            session_id=analysis_session.id,
            statistics=statistics,
            insights=insights,
            created_at=analysis_session.created_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析エラー: {str(e)}")


@router.post("/market", response_model=MarketResearchResponse)
async def analyze_market(
    request: MarketResearchRequest,
    session: Session = Depends(get_session)
):
    """
    市場調査を実行
    
    - 競合施設のリサーチ
    - 口コミ分析
    - 地域トレンド分析
    """
    # 宿泊施設の存在確認
    hotel = session.get(Hotel, request.hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    try:
        llm_client = get_llm_client()
        
        # 競合リサーチ（現時点ではモックデータとAI分析）
        competitors_data = await _research_competitors(request.address, request.radius_km, llm_client)
        
        # 口コミ要約（現時点ではAIによる一般的な分析）
        reviews_summary = await _analyze_reviews(request.address, llm_client)
        
        # 地域トレンド分析
        regional_trends = await _analyze_regional_trends(request.address, llm_client)
        
        # 分析セッションを更新
        statement = select(AnalysisSession).where(AnalysisSession.hotel_id == request.hotel_id)
        analysis_session = session.exec(statement).first()
        
        if analysis_session:
            analysis_session.competitors_list = competitors_data
            analysis_session.reviews_summary = reviews_summary
            analysis_session.regional_trends = regional_trends
        else:
            analysis_session = AnalysisSession(
                hotel_id=request.hotel_id,
                competitors_list=competitors_data,
                reviews_summary=reviews_summary,
                regional_trends=regional_trends
            )
            session.add(analysis_session)
        
        session.commit()
        session.refresh(analysis_session)
        
        return MarketResearchResponse(
            session_id=analysis_session.id,
            competitors=competitors_data,
            reviews_summary=reviews_summary,
            regional_trends=regional_trends,
            created_at=analysis_session.created_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"市場調査エラー: {str(e)}")


async def _research_competitors(address: str, radius_km: float, llm_client) -> dict:
    """競合をリサーチ（現時点ではAIベースの分析）"""
    prompt = f"""
{address}周辺{radius_km}km圏内の宿泊施設の競合状況について、一般的な市場動向を分析してください。

以下の項目を含むJSON形式で出力してください：
{{
    "area_type": "地域タイプ（観光地/ビジネス街/温泉地など）",
    "estimated_competitors": "推定競合数",
    "price_range": {{
        "low": 最低価格帯,
        "average": 平均価格帯,
        "high": 最高価格帯
    }},
    "competitive_factors": ["競合の強み1", "競合の強み2", "競合の強み3"]
}}
"""
    
    response = await llm_client.generate_structured_output(
        user_prompt=prompt,
        system_prompt="あなたは宿泊業界のマーケットリサーチャーです。"
    )
    
    import json, re
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(response)
    except:
        return {
            "area_type": "不明",
            "estimated_competitors": "データ取得中",
            "price_range": {"low": 0, "average": 0, "high": 0},
            "competitive_factors": []
        }


async def _analyze_reviews(address: str, llm_client) -> dict:
    """口コミを分析（現時点ではAIベースの分析）"""
    prompt = f"""
{address}エリアの宿泊施設に対する一般的な口コミ傾向を分析してください。

以下の項目を含むJSON形式で出力してください：
{{
    "positive_themes": ["好評ポイント1", "好評ポイント2", "好評ポイント3"],
    "negative_themes": ["不評ポイント1", "不評ポイント2", "不評ポイント3"],
    "guest_expectations": ["お客様の期待1", "お客様の期待2", "お客様の期待3"]
}}
"""
    
    response = await llm_client.generate_structured_output(
        user_prompt=prompt,
        system_prompt="あなたは口コミ分析の専門家です。"
    )
    
    import json, re
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(response)
    except:
        return {
            "positive_themes": [],
            "negative_themes": [],
            "guest_expectations": []
        }


async def _analyze_regional_trends(address: str, llm_client) -> str:
    """地域トレンドを分析"""
    prompt = f"""
{address}エリアにおける宿泊業界のトレンドと市場機会について、800文字程度で分析してください。

以下の観点を含めてください：
1. 地域の特性と強み
2. 観光トレンド
3. 今後の市場機会
4. 推奨される戦略方向性
"""
    
    response = await llm_client.generate_text(
        user_prompt=prompt,
        system_prompt="あなたは地域観光と宿泊業界のトレンドアナリストです。",
        max_tokens=2000
    )
    
    return response


