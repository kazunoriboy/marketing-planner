from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.core.database import get_session
from app.core.llm import get_llm_client
from app.models import AnalysisSession, MarketingPlan, PlanStatus, Hotel, FacilityAdminHotel
from app.schemas.planning import (
    PlanGenerationRequest,
    MarketingPlanResponse,
    PlanApprovalRequest,
    PlanSectionEditRequest
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
    """
    # 施設の分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    plan = session.get(MarketingPlan, plan_id)
    if not plan or plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    try:
        # プラン生成サービスを初期化
        generator = PlanGenerator()
        llm_client = get_llm_client(model_name="gemini-3-flash-preview")
        
        # プラン全体を修正
        edited_plan_data = await generator.edit_section(
            plan=plan,
            section=request.section,
            instruction=request.instruction,
            llm_client=llm_client
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


