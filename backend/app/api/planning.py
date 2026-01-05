from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from pydantic import BaseModel

from app.core.database import get_session
from app.core.llm import get_llm_client
from app.models import AnalysisSession, MarketingPlan, PlanStatus, Hotel, FacilityAdminHotel, ExistingPlan
from app.schemas.planning import (
    PlanGenerationRequest,
    MarketingPlanResponse,
    PlanApprovalRequest,
    PlanSectionEditRequest,
    ExistingPlanCreate,
    ExistingPlanUpdate,
    ExistingPlanResponse,
    ExistingPlanBasedGenerationRequest
)
from app.services.plan_generator import PlanGenerator
from app.auth.dependencies import require_hotel_access, require_hotel_editor

router = APIRouter(prefix="/api/planning", tags=["planning"])


# ============================================
# 施設認証付きエンドポイント（マルチテナント対応）
# ============================================

@router.post("/hotels/{hotel_id}/generate", response_model=List[MarketingPlanResponse])
async def generate_marketing_plans_authenticated(
    hotel_id: int,
    num_plans: int = 3,
    persona_index: int = None,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    マーケティングプランを生成（認証付き）
    
    - 施設の分析セッションを取得
    - 顧客分析結果と市場調査結果を基にプラン案を生成
    - 3C分析・PEST分析を含む戦略的なプランを作成
    - persona_index: 特定のペルソナに対してプランを生成する場合に指定（0始まり）
    """
    # 施設の分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        raise HTTPException(
            status_code=404,
            detail="分析セッションが見つかりません。先に顧客分析または市場調査を実行してください。"
        )
    
    # 分析データの存在確認
    if not analysis_session.csv_statistics and not analysis_session.competitors_list:
        raise HTTPException(
            status_code=400,
            detail="分析データが不足しています。先に顧客分析または市場調査を実行してください。"
        )
    
    # ペルソナインデックスの検証
    if persona_index is not None:
        personas = analysis_session.personas or []
        if persona_index < 0 or persona_index >= len(personas):
            raise HTTPException(
                status_code=400,
                detail=f"無効なペルソナインデックスです。0〜{len(personas)-1}の範囲で指定してください。"
            )
    
    try:
        # プラン生成サービスを初期化
        generator = PlanGenerator()
        llm_client = get_llm_client()
        
        # プランを生成
        plans_data = await generator.generate_plans(
            analysis_session=analysis_session,
            num_plans=num_plans,
            llm_client=llm_client,
            persona_index=persona_index
        )
        
        # データベースに保存
        saved_plans = []
        for plan_data in plans_data:
            marketing_plan = MarketingPlan(
                analysis_session_id=analysis_session.id,
                status=PlanStatus.draft,
                plan_name=plan_data["plan_name"],
                concept=plan_data["concept"],
                target_audience=plan_data["target_audience"],
                price_range=plan_data["price_range"],
                benefits=plan_data["benefits"],
                strategy_3c=plan_data["strategy_3c"],
                strategy_pest=plan_data["strategy_pest"]
            )
            session.add(marketing_plan)
            saved_plans.append(marketing_plan)
        
        session.commit()
        
        # 保存したプランをリフレッシュ
        for plan in saved_plans:
            session.refresh(plan)
        
        return saved_plans
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"プラン生成エラー: {str(e)}")


@router.get("/hotels/{hotel_id}/plans", response_model=List[MarketingPlanResponse])
async def list_plans_by_hotel(
    hotel_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """施設のプラン一覧を取得（認証付き）"""
    # 施設の分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        return []
    
    statement = select(MarketingPlan).where(MarketingPlan.analysis_session_id == analysis_session.id)
    plans = session.exec(statement).all()
    return plans


@router.get("/hotels/{hotel_id}/plans/{plan_id}", response_model=MarketingPlanResponse)
async def get_plan_by_hotel(
    hotel_id: int,
    plan_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """施設のプラン詳細を取得（認証付き）"""
    # 施設の分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    plan = session.get(MarketingPlan, plan_id)
    if not plan or plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    return plan


@router.put("/hotels/{hotel_id}/plans/{plan_id}/status", response_model=MarketingPlanResponse)
async def update_plan_status_authenticated(
    hotel_id: int,
    plan_id: int,
    request: PlanApprovalRequest,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """プランのステータスを更新（認証付き、編集者以上）"""
    # 施設の分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    plan = session.get(MarketingPlan, plan_id)
    if not plan or plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    plan.status = request.status
    session.add(plan)
    session.commit()
    session.refresh(plan)
    
    return plan


@router.delete("/hotels/{hotel_id}/plans/{plan_id}")
async def delete_plan_authenticated(
    hotel_id: int,
    plan_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """プランを削除（認証付き、編集者以上）"""
    # 施設の分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    plan = session.get(MarketingPlan, plan_id)
    if not plan or plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    session.delete(plan)
    session.commit()
    
    return {"message": "プランを削除しました", "plan_id": plan_id}


@router.put("/hotels/{hotel_id}/plans/{plan_id}/edit-section", response_model=MarketingPlanResponse)
async def edit_plan_section(
    hotel_id: int,
    plan_id: int,
    request: PlanSectionEditRequest,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """
    プランを修正指示に基づいて全体調整（認証付き、編集者以上）
    
    - section: 修正の起点となるセクション（concept, target_audience, price_range, benefits）
    - instruction: 修正指示（例: "地元の名士との交流を削除して、料理体験に焦点を当てて"）
    
    指定されたセクションの修正指示に基づいて、プラン全体の一貫性を保つように調整します。
    プラン名、コンセプト、ターゲット顧客、価格帯の根拠、特典など、関連するすべての箇所が更新されます。
    
    ※ 分析セッションのペルソナ、顧客データ分析、口コミ分析なども考慮して修正されます。
    """
    # 施設情報を取得（資産情報含む）
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="施設が見つかりません")
    
    # 施設の分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    # プランを取得（analysis_session_idがOptionalなので柔軟に対応）
    plan = session.get(MarketingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    # プランが分析セッションに紐づいている場合は整合性を確認
    if plan.analysis_session_id and analysis_session and plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    # 既存プランを取得
    existing_plans_statement = select(ExistingPlan).where(ExistingPlan.hotel_id == hotel_id)
    existing_plans = session.exec(existing_plans_statement).all()
    existing_plans_data = [
        {
            "plan_title": ep.plan_title,
            "plan_description": ep.plan_description,
            "room_facilities": ep.room_facilities,
            "hotel_assets": ep.hotel_assets,
        }
        for ep in existing_plans
    ]
    
    try:
        # プラン生成サービスを初期化
        generator = PlanGenerator()
        llm_client = get_llm_client(model_name="gemini-3-flash-preview")
        
        # プラン全体を修正（分析データと資産情報を含めて）
        edited_plan_data = await generator.edit_section(
            plan=plan,
            section=request.section,
            instruction=request.instruction,
            llm_client=llm_client,
            analysis_session=analysis_session,
            hotel_assets=hotel.hotel_assets if hotel.hotel_assets else None,
            existing_plans=existing_plans_data if existing_plans_data else None
        )
        
        # プラン全体を更新
        plan.plan_name = edited_plan_data["plan_name"]
        plan.concept = edited_plan_data["concept"]
        plan.target_audience = edited_plan_data["target_audience"]
        plan.price_range = edited_plan_data["price_range"]
        plan.benefits = edited_plan_data["benefits"]
        plan.strategy_3c = edited_plan_data["strategy_3c"]
        plan.strategy_pest = edited_plan_data["strategy_pest"]
        
        session.add(plan)
        session.commit()
        session.refresh(plan)
        
        return plan
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"プラン修正エラー: {str(e)}")


# ============================================
# 既存プラン管理エンドポイント（宿の運用中プラン）
# ============================================

@router.get("/hotels/{hotel_id}/existing-plans", response_model=List[ExistingPlanResponse])
async def list_existing_plans(
    hotel_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """宿の既存プラン一覧を取得"""
    statement = select(ExistingPlan).where(
        ExistingPlan.hotel_id == hotel_id,
        ExistingPlan.is_active == True
    )
    plans = session.exec(statement).all()
    return plans


@router.post("/hotels/{hotel_id}/existing-plans", response_model=ExistingPlanResponse)
async def create_existing_plan(
    hotel_id: int,
    request: ExistingPlanCreate,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """既存プランを登録"""
    existing_plan = ExistingPlan(
        hotel_id=hotel_id,
        plan_title=request.plan_title,
        plan_description=request.plan_description,
        room_facilities=request.room_facilities,
        hotel_assets=request.hotel_assets,
        price_info=request.price_info,
        meal_info=request.meal_info,
        notes=request.notes
    )
    session.add(existing_plan)
    session.commit()
    session.refresh(existing_plan)
    return existing_plan


@router.get("/hotels/{hotel_id}/existing-plans/{plan_id}", response_model=ExistingPlanResponse)
async def get_existing_plan(
    hotel_id: int,
    plan_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """既存プランの詳細を取得"""
    plan = session.get(ExistingPlan, plan_id)
    if not plan or plan.hotel_id != hotel_id:
        raise HTTPException(status_code=404, detail="既存プランが見つかりません")
    return plan


@router.put("/hotels/{hotel_id}/existing-plans/{plan_id}", response_model=ExistingPlanResponse)
async def update_existing_plan(
    hotel_id: int,
    plan_id: int,
    request: ExistingPlanUpdate,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """既存プランを更新"""
    plan = session.get(ExistingPlan, plan_id)
    if not plan or plan.hotel_id != hotel_id:
        raise HTTPException(status_code=404, detail="既存プランが見つかりません")
    
    # 更新対象のフィールドのみ更新
    if request.plan_title is not None:
        plan.plan_title = request.plan_title
    if request.plan_description is not None:
        plan.plan_description = request.plan_description
    if request.room_facilities is not None:
        plan.room_facilities = request.room_facilities
    if request.hotel_assets is not None:
        plan.hotel_assets = request.hotel_assets
    if request.price_info is not None:
        plan.price_info = request.price_info
    if request.meal_info is not None:
        plan.meal_info = request.meal_info
    if request.notes is not None:
        plan.notes = request.notes
    if request.is_active is not None:
        plan.is_active = request.is_active
    
    from datetime import datetime
    plan.updated_at = datetime.utcnow()
    
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


@router.delete("/hotels/{hotel_id}/existing-plans/{plan_id}")
async def delete_existing_plan(
    hotel_id: int,
    plan_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """既存プランを削除（物理削除）"""
    plan = session.get(ExistingPlan, plan_id)
    if not plan or plan.hotel_id != hotel_id:
        raise HTTPException(status_code=404, detail="既存プランが見つかりません")
    
    session.delete(plan)
    session.commit()
    
    return {"message": "既存プランを削除しました", "plan_id": plan_id}


@router.post("/hotels/{hotel_id}/generate-from-existing", response_model=List[MarketingPlanResponse])
async def generate_plans_from_existing(
    hotel_id: int,
    request: ExistingPlanBasedGenerationRequest,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    既存プランをベースにマーケティングプランを生成
    
    - 既存プランの内容（部屋設備、宿の資産など）を活かしつつ
    - ペルソナに合わせた見せ方・訴求方法を変えたプランを生成
    """
    # 既存プランの取得
    existing_plan = session.get(ExistingPlan, request.existing_plan_id)
    if not existing_plan or existing_plan.hotel_id != hotel_id:
        raise HTTPException(status_code=404, detail="既存プランが見つかりません")
    
    # 分析セッションの取得（ペルソナ情報のため）
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    # ペルソナインデックスの検証
    target_persona = None
    if request.persona_index is not None:
        if not analysis_session or not analysis_session.personas:
            raise HTTPException(
                status_code=400,
                detail="ペルソナを使用するには、先に「顧客を知る」でペルソナを生成してください。"
            )
        personas = analysis_session.personas
        if request.persona_index < 0 or request.persona_index >= len(personas):
            raise HTTPException(
                status_code=400,
                detail=f"無効なペルソナインデックスです。0〜{len(personas)-1}の範囲で指定してください。"
            )
        target_persona = personas[request.persona_index]
    
    try:
        # プラン生成サービスを初期化
        generator = PlanGenerator()
        llm_client = get_llm_client()
        
        # 既存プランベースでプランを生成
        plans_data = await generator.generate_plans_from_existing(
            existing_plan=existing_plan,
            target_persona=target_persona,
            num_plans=request.num_plans,
            llm_client=llm_client
        )
        
        # データベースに保存
        saved_plans = []
        for plan_data in plans_data:
            # analysis_session_idはオプショナル（ない場合もある）
            analysis_session_id = analysis_session.id if analysis_session else None
            
            marketing_plan = MarketingPlan(
                analysis_session_id=analysis_session_id,
                status=PlanStatus.draft,
                plan_name=plan_data["plan_name"],
                concept=plan_data["concept"],
                target_audience=plan_data["target_audience"],
                price_range=plan_data["price_range"],
                benefits=plan_data["benefits"],
                strategy_3c=plan_data["strategy_3c"],
                strategy_pest=plan_data["strategy_pest"]
            )
            session.add(marketing_plan)
            saved_plans.append(marketing_plan)
        
        session.commit()
        
        # 保存したプランをリフレッシュ
        for plan in saved_plans:
            session.refresh(plan)
        
        return saved_plans
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"プラン生成エラー: {str(e)}")


class AssetsBasedGenerationRequest(BaseModel):
    """施設の資産ベースのプラン生成リクエスト"""
    num_plans: int = 3
    persona_index: int = None


@router.post("/hotels/{hotel_id}/generate-from-assets", response_model=List[MarketingPlanResponse])
async def generate_plans_from_assets(
    hotel_id: int,
    request: AssetsBasedGenerationRequest,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    施設の資産＋既存プラン全体からマーケティングプランを生成
    
    - 施設に登録された資産（設備、料理、サービス等）
    - 登録されている既存プラン
    - これらの情報から、施設が提供できる価値を把握してプランを生成
    """
    # 施設情報を取得
    hotel = session.get(Hotel, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="施設が見つかりません")
    
    # 施設の資産を取得
    hotel_assets = hotel.hotel_assets or {}
    
    # 既存プラン一覧を取得
    statement = select(ExistingPlan).where(
        ExistingPlan.hotel_id == hotel_id,
        ExistingPlan.is_active == True
    )
    existing_plans = session.exec(statement).all()
    
    # 資産または既存プランのいずれかが必要
    has_assets = any(len(v) > 0 for v in hotel_assets.values() if isinstance(v, list))
    if not has_assets and len(existing_plans) == 0:
        raise HTTPException(
            status_code=400,
            detail="施設の資産または既存プランを登録してください"
        )
    
    # 分析セッションの取得（ペルソナ情報のため）
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    # ペルソナインデックスの検証
    target_persona = None
    if request.persona_index is not None:
        if not analysis_session or not analysis_session.personas:
            raise HTTPException(
                status_code=400,
                detail="ペルソナを使用するには、先に「顧客を知る」でペルソナを生成してください。"
            )
        personas = analysis_session.personas
        if request.persona_index < 0 or request.persona_index >= len(personas):
            raise HTTPException(
                status_code=400,
                detail=f"無効なペルソナインデックスです。0〜{len(personas)-1}の範囲で指定してください。"
            )
        target_persona = personas[request.persona_index]
    
    try:
        # プラン生成サービスを初期化
        generator = PlanGenerator()
        llm_client = get_llm_client()
        
        # 施設の資産＋既存プラン全体からプランを生成
        plans_data = await generator.generate_plans_from_assets(
            hotel_assets=hotel_assets,
            existing_plans=[{
                "plan_title": ep.plan_title,
                "plan_description": ep.plan_description,
                "room_facilities": ep.room_facilities,
                "hotel_assets": ep.hotel_assets,
                "price_info": ep.price_info,
                "meal_info": ep.meal_info,
            } for ep in existing_plans],
            target_persona=target_persona,
            num_plans=request.num_plans,
            llm_client=llm_client
        )
        
        # データベースに保存
        saved_plans = []
        for plan_data in plans_data:
            analysis_session_id = analysis_session.id if analysis_session else None
            
            marketing_plan = MarketingPlan(
                analysis_session_id=analysis_session_id,
                status=PlanStatus.draft,
                plan_name=plan_data["plan_name"],
                concept=plan_data["concept"],
                target_audience=plan_data["target_audience"],
                price_range=plan_data["price_range"],
                benefits=plan_data["benefits"],
                strategy_3c=plan_data["strategy_3c"],
                strategy_pest=plan_data["strategy_pest"]
            )
            session.add(marketing_plan)
            saved_plans.append(marketing_plan)
        
        session.commit()
        
        for plan in saved_plans:
            session.refresh(plan)
        
        return saved_plans
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"プラン生成エラー: {str(e)}")


# ============================================
# 既存エンドポイント（後方互換性のため保持）
# ============================================


@router.post("/generate", response_model=List[MarketingPlanResponse])
async def generate_marketing_plans(
    request: PlanGenerationRequest,
    session: Session = Depends(get_session)
):
    """
    マーケティングプランを生成
    
    - 分析セッションIDを受け取る
    - 顧客分析結果と市場調査結果を基にプラン案を生成
    - 3C分析・PEST分析を含む戦略的なプランを作成
    """
    # 分析セッションの存在確認
    analysis_session = session.get(AnalysisSession, request.analysis_session_id)
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    # 分析データの存在確認
    if not analysis_session.csv_statistics and not analysis_session.competitors_list:
        raise HTTPException(
            status_code=400,
            detail="分析データが不足しています。先に顧客分析または市場調査を実行してください。"
        )
    
    try:
        # プラン生成サービスを初期化
        generator = PlanGenerator()
        llm_client = get_llm_client()
        
        # プランを生成
        plans_data = await generator.generate_plans(
            analysis_session=analysis_session,
            num_plans=request.num_plans,
            llm_client=llm_client
        )
        
        # データベースに保存
        saved_plans = []
        for plan_data in plans_data:
            marketing_plan = MarketingPlan(
                analysis_session_id=request.analysis_session_id,
                status=PlanStatus.draft,
                plan_name=plan_data["plan_name"],
                concept=plan_data["concept"],
                target_audience=plan_data["target_audience"],
                price_range=plan_data["price_range"],
                benefits=plan_data["benefits"],
                strategy_3c=plan_data["strategy_3c"],
                strategy_pest=plan_data["strategy_pest"]
            )
            session.add(marketing_plan)
            saved_plans.append(marketing_plan)
        
        session.commit()
        
        # 保存したプランをリフレッシュ
        for plan in saved_plans:
            session.refresh(plan)
        
        return saved_plans
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"プラン生成エラー: {str(e)}")


@router.get("/plans/{plan_id}", response_model=MarketingPlanResponse)
async def get_marketing_plan(
    plan_id: int,
    session: Session = Depends(get_session)
):
    """マーケティングプランの詳細を取得"""
    plan = session.get(MarketingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    return plan


@router.get("/sessions/{session_id}/plans", response_model=List[MarketingPlanResponse])
async def list_plans_by_session(
    session_id: int,
    session: Session = Depends(get_session)
):
    """特定の分析セッションに紐づくプラン一覧を取得"""
    statement = select(MarketingPlan).where(MarketingPlan.analysis_session_id == session_id)
    plans = session.exec(statement).all()
    return plans


@router.put("/plans/{plan_id}/status", response_model=MarketingPlanResponse)
async def update_plan_status(
    plan_id: int,
    request: PlanApprovalRequest,
    session: Session = Depends(get_session)
):
    """プランのステータスを更新（承認/ドラフト）"""
    plan = session.get(MarketingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    plan.status = request.status
    session.add(plan)
    session.commit()
    session.refresh(plan)
    
    return plan


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    session: Session = Depends(get_session)
):
    """プランを削除"""
    plan = session.get(MarketingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    session.delete(plan)
    session.commit()
    
    return {"message": "プランを削除しました", "plan_id": plan_id}


