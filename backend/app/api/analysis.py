from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from typing import List
from datetime import datetime

from app.core.database import get_session
from app.core.llm import get_llm_client
from app.models import Hotel, AnalysisSession, FacilityAdmin, FacilityAdminHotel
from app.schemas.analysis import (
    HotelCreate,
    HotelResponse,
    CSVAnalysisResponse,
    MarketResearchRequest,
    MarketResearchResponse,
    ReviewUrlsUpdate,
    ReviewUrlsResponse,
    ReviewAnalysisResponse,
    PersonaGenerationResponse,
    PersonasResponse,
    Persona,
    PersonaEditRequest,
    PersonaEditResponse,
)
from app.services.csv_analyzer import CSVAnalyzer
from app.services.analysis_service import AnalysisService
from app.services.review_service import get_review_service
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
    filename = file.filename or ""
    content_type = file.content_type or ""
    is_csv = (
        filename.lower().endswith('.csv') or
        content_type in ["text/csv", "application/csv", "text/plain"]
    )
    if not is_csv:
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
    filename = file.filename or ""
    content_type = file.content_type or ""
    
    # ファイル名またはContent-Typeで検証
    is_csv = (
        filename.lower().endswith('.csv') or
        content_type in ["text/csv", "application/csv", "text/plain"]
    )
    
    if not is_csv:
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
    filename = file.filename or ""
    content_type = file.content_type or ""
    is_csv = (
        filename.lower().endswith('.csv') or
        content_type in ["text/csv", "application/csv", "text/plain"]
    )
    if not is_csv:
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
    filename = file.filename or ""
    content_type = file.content_type or ""
    is_csv = (
        filename.lower().endswith('.csv') or
        content_type in ["text/csv", "application/csv", "text/plain"]
    )
    if not is_csv:
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


# ============================================
# 口コミ収集・分析エンドポイント
# ============================================

@router.get("/hotels/{hotel_id}/review-urls", response_model=ReviewUrlsResponse)
async def get_review_urls(
    hotel_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    口コミURLを取得
    
    登録されている口コミページのURLを取得します。
    """
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    return ReviewUrlsResponse(
        hotel_id=hotel_id,
        review_urls=hotel.review_urls or {},
        updated_at=hotel.updated_at
    )


@router.put("/hotels/{hotel_id}/review-urls", response_model=ReviewUrlsResponse)
async def update_review_urls(
    hotel_id: int,
    urls: ReviewUrlsUpdate,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    口コミURLを登録・更新
    
    じゃらん、Googleマップなどの口コミページURLを登録します。
    """
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    # URLの検証
    review_service = get_review_service()
    
    new_urls = {}
    if urls.jalan:
        if not review_service.validate_url(urls.jalan, "jalan"):
            raise HTTPException(
                status_code=400,
                detail="じゃらんのURLの形式が不正です"
            )
        new_urls["jalan"] = urls.jalan
    
    if urls.google:
        if not review_service.validate_url(urls.google, "google"):
            raise HTTPException(
                status_code=400,
                detail="GoogleマップのURLの形式が不正です"
            )
        new_urls["google"] = urls.google
    
    # 既存のURLとマージ
    current_urls = hotel.review_urls or {}
    current_urls.update(new_urls)
    
    hotel.review_urls = current_urls
    hotel.updated_at = datetime.utcnow()
    
    session.add(hotel)
    session.commit()
    session.refresh(hotel)
    
    return ReviewUrlsResponse(
        hotel_id=hotel_id,
        review_urls=hotel.review_urls,
        updated_at=hotel.updated_at
    )


@router.post("/hotels/{hotel_id}/reviews/analyze", response_model=ReviewAnalysisResponse)
async def analyze_reviews(
    hotel_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    口コミを収集・分析
    
    登録されている口コミURLからDify + Jina Readerを使用して
    口コミを収集し、分析結果を保存します。
    """
    print(f"[DEBUG] analyze_reviews called for hotel_id={hotel_id}")
    
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    review_urls = hotel.review_urls or {}
    print(f"[DEBUG] review_urls: {review_urls}")
    
    if not review_urls:
        raise HTTPException(
            status_code=400,
            detail="口コミURLが登録されていません。先にURLを登録してください。"
        )
    
    try:
        # 口コミ収集・分析を実行
        print("[DEBUG] Creating review_service...")
        review_service = get_review_service()
        print("[DEBUG] Calling analyze_multiple_sources...")
        analysis_result = await review_service.analyze_multiple_sources(review_urls)
        print(f"[DEBUG] analysis_result: {analysis_result}")
        
        # reviews_summary形式に変換
        reviews_summary = review_service.format_for_reviews_summary(analysis_result)
        
        # 分析セッションを更新
        statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
        analysis_session = session.exec(statement).first()
        
        if analysis_session:
            analysis_session.reviews_summary = reviews_summary
            analysis_session.updated_at = datetime.utcnow()
        else:
            analysis_session = AnalysisSession(
                hotel_id=hotel_id,
                reviews_summary=reviews_summary
            )
            session.add(analysis_session)
        
        session.commit()
        session.refresh(analysis_session)
        
        return ReviewAnalysisResponse(
            session_id=analysis_session.id,
            reviews_summary=reviews_summary,
            sources=analysis_result.get("sources", []),
            total_reviews=reviews_summary.get("total_reviews", 0),
            analyzed_at=datetime.utcnow()
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"口コミ分析エラー: {str(e)}"
        )


# ============================================
# ペルソナ生成エンドポイント
# ============================================

@router.post("/hotels/{hotel_id}/personas/generate", response_model=PersonaGenerationResponse)
async def generate_personas(
    hotel_id: int,
    num_personas: int = 3,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    ペルソナを生成
    
    分析データ（CSVの統計情報、口コミ分析結果）をもとに
    AIがターゲット顧客のペルソナを生成します。
    """
    # 宿泊施設の存在確認
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    # 分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        raise HTTPException(
            status_code=400,
            detail="分析データがありません。先に顧客データまたは口コミの分析を行ってください。"
        )
    
    # 分析データがあるか確認
    has_csv_data = analysis_session.csv_statistics and len(analysis_session.csv_statistics) > 0
    has_review_data = analysis_session.reviews_summary and len(analysis_session.reviews_summary) > 0
    
    if not has_csv_data and not has_review_data:
        raise HTTPException(
            status_code=400,
            detail="分析データがありません。先に顧客データまたは口コミの分析を行ってください。"
        )
    
    try:
        # LLMを使ってペルソナを生成
        llm_client = get_llm_client(model_name="gemini-2.5-flash-lite")
        personas = await _generate_personas_with_llm(
            llm_client=llm_client,
            hotel=hotel,
            csv_statistics=analysis_session.csv_statistics if has_csv_data else None,
            csv_insights=analysis_session.csv_insights if has_csv_data else None,
            reviews_summary=analysis_session.reviews_summary if has_review_data else None,
            num_personas=num_personas
        )
        
        # 分析セッションを更新
        analysis_session.personas = personas
        analysis_session.updated_at = datetime.utcnow()
        session.add(analysis_session)
        session.commit()
        session.refresh(analysis_session)
        
        return PersonaGenerationResponse(
            session_id=analysis_session.id,
            personas=[Persona(**p) for p in personas],
            generated_at=datetime.utcnow()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ペルソナ生成エラー: {str(e)}"
        )


@router.get("/hotels/{hotel_id}/personas", response_model=PersonasResponse)
async def get_personas(
    hotel_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    生成済みのペルソナを取得
    """
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        return PersonasResponse(
            session_id=0,
            personas=[],
            updated_at=None
        )
    
    return PersonasResponse(
        session_id=analysis_session.id,
        personas=analysis_session.personas or [],
        updated_at=analysis_session.updated_at
    )


async def _generate_personas_with_llm(
    llm_client,
    hotel: Hotel,
    csv_statistics: dict | None,
    csv_insights: str | None,
    reviews_summary: dict | None,
    num_personas: int = 3
) -> list:
    """LLMを使ってペルソナを生成"""
    import json
    import re
    
    # 分析データを整理
    analysis_context = f"""
## 宿泊施設情報
- 施設名: {hotel.name}
- 住所: {hotel.address}
"""
    
    if csv_statistics:
        analysis_context += f"""
## 顧客データ分析結果
```json
{json.dumps(csv_statistics, ensure_ascii=False, indent=2)}
```
"""
    
    if csv_insights:
        analysis_context += f"""
## 顧客データからのインサイト
{csv_insights}
"""
    
    if reviews_summary:
        analysis_context += f"""
## 口コミ分析結果
```json
{json.dumps(reviews_summary, ensure_ascii=False, indent=2)}
```
"""
    
    prompt = f"""
以下の宿泊施設の分析データをもとに、ターゲット顧客のペルソナを{num_personas}人分作成してください。

{analysis_context}

## 出力形式
以下のJSON形式で{num_personas}人分のペルソナを配列として出力してください。
各ペルソナは具体的で、分析データに基づいた現実的な人物像にしてください。

```json
[
  {{
    "name": "架空の日本人名（フルネーム）",
    "age_range": "年齢層（例: 30代後半）",
    "gender": "性別",
    "location": "住んでいる場所（例: 東京都世田谷区、大阪府大阪市など）",
    "occupation": "職業（具体的に）",
    "travel_purpose": "旅行の主な目的",
    "values": ["重視すること1", "重視すること2", "重視すること3"],
    "budget_range": "1泊あたりの予算帯（例: 1万5千〜2万円）",
    "information_source": ["情報収集に使うメディア1", "情報収集に使うメディア2"],
    "needs": ["宿泊施設に求めること1", "宿泊施設に求めること2", "宿泊施設に求めること3"],
    "pain_points": ["旅行に関する悩み1", "旅行に関する悩み2"],
    "description": "このペルソナの詳細な説明（100〜150文字程度）。どんな人物で、なぜこの宿を選ぶのか、どんな体験を期待しているのかを具体的に。",
    "rationale": "このペルソナを作成した根拠。分析データのどの部分（例: 予約者エリアの〇〇が多い、価格帯が〇〇円、口コミで〇〇が評価されているなど）からこのペルソナを導き出したかを具体的に説明。"
  }}
]
```

## 注意事項
- 分析データに基づいた現実的なペルソナを作成してください
- 各ペルソナは異なる特徴を持つようにしてください（年齢層、旅行目的、予算帯、住んでいる場所などが被らないように）
- locationは宿泊施設へのアクセスを考慮して、現実的な居住地を設定してください
- rationaleには必ず分析データの具体的な数値や傾向を引用してください（例: 「関東からの予約が65%を占める」「平均単価が2万円」「口コミで温泉が好評」など）
- 日本語で出力してください
- JSON配列のみを出力し、余計な説明は不要です
"""
    
    response = await llm_client.generate_structured_output(
        user_prompt=prompt,
        system_prompt="あなたは宿泊業界のマーケティングエキスパートです。顧客分析データに基づいて、具体的で実用的なペルソナを作成します。",
        max_tokens=4096
    )
    
    # JSONをパース
    try:
        # コードブロックを除去
        json_str = response.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        
        # JSON配列を抽出
        json_match = re.search(r'\[.*\]', json_str, re.DOTALL)
        if json_match:
            personas = json.loads(json_match.group())
        else:
            personas = json.loads(json_str)
        
        # 必須フィールドの検証
        required_fields = ["name", "age_range", "gender", "location", "occupation", "travel_purpose", 
                          "values", "budget_range", "information_source", "needs", 
                          "pain_points", "description", "rationale"]
        
        validated_personas = []
        for persona in personas[:num_personas]:
            # 欠けているフィールドにデフォルト値を設定
            for field in required_fields:
                if field not in persona:
                    if field in ["values", "information_source", "needs", "pain_points"]:
                        persona[field] = []
                    else:
                        persona[field] = "未設定"
            validated_personas.append(persona)
        
        return validated_personas
    
    except json.JSONDecodeError as e:
        raise Exception(f"ペルソナのJSON解析に失敗しました: {str(e)}")


@router.put("/hotels/{hotel_id}/personas/{persona_index}", response_model=PersonaEditResponse)
async def edit_persona(
    hotel_id: int,
    persona_index: int,
    request: PersonaEditRequest,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    ペルソナを修正
    
    指定したペルソナに対して修正指示を出し、AIが修正したペルソナを返します。
    """
    # 宿泊施設の存在確認
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="宿泊施設が見つかりません")
    
    # 分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session or not analysis_session.personas:
        raise HTTPException(status_code=404, detail="ペルソナが見つかりません")
    
    # インデックスの検証
    if persona_index < 0 or persona_index >= len(analysis_session.personas):
        raise HTTPException(
            status_code=400,
            detail=f"ペルソナのインデックスが不正です。0〜{len(analysis_session.personas) - 1}の範囲で指定してください。"
        )
    
    try:
        # LLMを使ってペルソナを修正
        llm_client = get_llm_client(model_name="gemini-2.5-flash-lite")
        current_persona = analysis_session.personas[persona_index]
        
        edited_persona = await _edit_persona_with_llm(
            llm_client=llm_client,
            current_persona=current_persona,
            instruction=request.instruction
        )
        
        # ペルソナを更新
        personas = list(analysis_session.personas)
        personas[persona_index] = edited_persona
        analysis_session.personas = personas
        analysis_session.updated_at = datetime.utcnow()
        
        session.add(analysis_session)
        session.commit()
        session.refresh(analysis_session)
        
        return PersonaEditResponse(
            session_id=analysis_session.id,
            persona=Persona(**edited_persona),
            persona_index=persona_index,
            updated_at=datetime.utcnow()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ペルソナ修正エラー: {str(e)}"
        )


async def _edit_persona_with_llm(
    llm_client,
    current_persona: dict,
    instruction: str
) -> dict:
    """LLMを使ってペルソナを修正"""
    import json
    import re
    
    prompt = f"""
以下のペルソナを、ユーザーの修正指示に従って修正してください。

## 現在のペルソナ
```json
{json.dumps(current_persona, ensure_ascii=False, indent=2)}
```

## 修正指示
{instruction}

## 出力形式
修正後のペルソナを以下のJSON形式で出力してください。
修正指示に関連する部分のみを変更し、他の部分は元のまま維持してください。

```json
{{
  "name": "架空の日本人名（フルネーム）",
  "age_range": "年齢層（例: 30代後半）",
  "gender": "性別",
  "location": "住んでいる場所（例: 東京都世田谷区）",
  "occupation": "職業（具体的に）",
  "travel_purpose": "旅行の主な目的",
  "values": ["重視すること1", "重視すること2", "重視すること3"],
  "budget_range": "1泊あたりの予算帯（例: 1万5千〜2万円）",
  "information_source": ["情報収集に使うメディア1", "情報収集に使うメディア2"],
  "needs": ["宿泊施設に求めること1", "宿泊施設に求めること2", "宿泊施設に求めること3"],
  "pain_points": ["旅行に関する悩み1", "旅行に関する悩み2"],
  "description": "このペルソナの詳細な説明",
  "rationale": "このペルソナを作成した根拠（修正後も、元の分析データに基づいた根拠を維持または更新）"
}}
```

## 注意事項
- 修正指示に関連する部分のみを変更してください
- 変更に伴い、descriptionとrationaleも適切に更新してください
- rationaleは元の分析データに基づいた根拠を維持しつつ、修正内容を反映させてください
- 日本語で出力してください
- JSONオブジェクトのみを出力し、余計な説明は不要です
"""
    
    response = await llm_client.generate_structured_output(
        user_prompt=prompt,
        system_prompt="あなたは宿泊業界のマーケティングエキスパートです。ペルソナの修正を行います。",
        max_tokens=2048
    )
    
    # JSONをパース
    try:
        # コードブロックを除去
        json_str = response.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        
        # JSONオブジェクトを抽出
        json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if json_match:
            edited_persona = json.loads(json_match.group())
        else:
            edited_persona = json.loads(json_str)
        
        # 必須フィールドの検証
        required_fields = ["name", "age_range", "gender", "location", "occupation", "travel_purpose", 
                          "values", "budget_range", "information_source", "needs", 
                          "pain_points", "description", "rationale"]
        
        for field in required_fields:
            if field not in edited_persona:
                # 元のペルソナから値を引き継ぐ
                if field in current_persona:
                    edited_persona[field] = current_persona[field]
                elif field in ["values", "information_source", "needs", "pain_points"]:
                    edited_persona[field] = []
                else:
                    edited_persona[field] = "未設定"
        
        return edited_persona
    
    except json.JSONDecodeError as e:
        raise Exception(f"ペルソナのJSON解析に失敗しました: {str(e)}")

