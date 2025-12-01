from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.core.database import get_session
from app.core.llm import get_llm_client
from app.models import AnalysisSession, MarketingPlan, PlanStatus
from app.schemas.planning import (
    PlanGenerationRequest,
    MarketingPlanResponse,
    PlanApprovalRequest
)
from app.services.plan_generator import PlanGenerator

router = APIRouter(prefix="/api/planning", tags=["planning"])


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


