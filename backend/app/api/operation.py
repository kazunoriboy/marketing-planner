from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime

from app.core.database import get_session
from app.core.llm import get_llm_client
from app.models import (
    AnalysisSession,
    MarketingPlan,
    PlanStatus,
    OperationManual,
    OperationManualStatus,
    OperationChatMessage,
    FacilityAdminHotel
)
from app.schemas.operation import (
    ChatMessageRequest,
    ChatMessageResponse,
    OperationManualResponse,
    OperationManualDetailResponse,
    GenerateManualRequest
)
from app.services.operation_service import OperationService
from app.auth.dependencies import require_hotel_access, require_hotel_editor

router = APIRouter(prefix="/api/operation", tags=["operation"])


@router.post("/hotels/{hotel_id}/plans/{plan_id}/start", response_model=OperationManualDetailResponse)
async def start_operation_chat(
    hotel_id: int,
    plan_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """
    オペレーションチャットを開始（または既存のセッションを取得）
    
    - 承認済みプランに対してのみ開始可能
    - 既存のマニュアルがある場合はそれを返す
    """
    # 施設の分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    # プランを取得
    plan = session.get(MarketingPlan, plan_id)
    if not plan or plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    # 承認済みチェック
    if plan.status != PlanStatus.approved:
        raise HTTPException(status_code=400, detail="プランが承認されていません。承認後にオペレーション作成を開始できます。")
    
    # 既存のマニュアルを確認
    statement = select(OperationManual).where(OperationManual.marketing_plan_id == plan_id)
    existing_manual = session.exec(statement).first()
    
    if existing_manual:
        # 既存のチャット履歴を取得
        messages_statement = select(OperationChatMessage).where(
            OperationChatMessage.operation_manual_id == existing_manual.id
        ).order_by(OperationChatMessage.created_at)
        messages = session.exec(messages_statement).all()
        
        return OperationManualDetailResponse(
            id=existing_manual.id,
            marketing_plan_id=existing_manual.marketing_plan_id,
            status=existing_manual.status,
            manual_content=existing_manual.manual_content,
            facility_context=existing_manual.facility_context,
            chat_messages=[ChatMessageResponse.model_validate(m) for m in messages],
            created_at=existing_manual.created_at,
            updated_at=existing_manual.updated_at
        )
    
    # 新規マニュアルを作成
    service = OperationService()
    initial_message = service.get_initial_message(plan)
    
    new_manual = OperationManual(
        marketing_plan_id=plan_id,
        status=OperationManualStatus.in_progress,
        manual_content={},
        facility_context={}
    )
    session.add(new_manual)
    session.commit()
    session.refresh(new_manual)
    
    # 初期メッセージを保存
    initial_chat = OperationChatMessage(
        operation_manual_id=new_manual.id,
        role="assistant",
        content=initial_message,
        msg_metadata={}
    )
    session.add(initial_chat)
    session.commit()
    session.refresh(initial_chat)
    
    return OperationManualDetailResponse(
        id=new_manual.id,
        marketing_plan_id=new_manual.marketing_plan_id,
        status=new_manual.status,
        manual_content=new_manual.manual_content,
        facility_context=new_manual.facility_context,
        chat_messages=[ChatMessageResponse.model_validate(initial_chat)],
        created_at=new_manual.created_at,
        updated_at=new_manual.updated_at
    )


@router.post("/hotels/{hotel_id}/manuals/{manual_id}/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    hotel_id: int,
    manual_id: int,
    request: ChatMessageRequest,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """
    チャットメッセージを送信してAI応答を取得
    """
    # マニュアルを取得
    manual = session.get(OperationManual, manual_id)
    if not manual:
        raise HTTPException(status_code=404, detail="オペレーションセッションが見つかりません")
    
    # プランを取得
    plan = session.get(MarketingPlan, manual.marketing_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    # 施設アクセス権確認
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    if not analysis_session or plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=403, detail="このプランへのアクセス権がありません")
    
    # 完了済みチェック
    if manual.status == OperationManualStatus.completed:
        raise HTTPException(status_code=400, detail="このセッションは既に完了しています")
    
    # ユーザーメッセージを保存
    user_message = OperationChatMessage(
        operation_manual_id=manual_id,
        role="user",
        content=request.message,
        msg_metadata={}
    )
    session.add(user_message)
    session.commit()
    
    # チャット履歴を取得
    messages_statement = select(OperationChatMessage).where(
        OperationChatMessage.operation_manual_id == manual_id
    ).order_by(OperationChatMessage.created_at)
    chat_history = list(session.exec(messages_statement).all())
    
    try:
        # AI応答を生成
        service = OperationService()
        llm_client = get_llm_client()
        
        result = await service.generate_chat_response(
            manual=manual,
            plan=plan,
            chat_history=chat_history,
            user_message=request.message,
            llm_client=llm_client
        )
        
        # 抽出されたコンテキストをマージ
        if result.get("extracted_context"):
            current_context = manual.facility_context or {}
            current_context.update(result["extracted_context"])
            manual.facility_context = current_context
            manual.updated_at = datetime.utcnow()
            session.add(manual)
        
        # AI応答を保存
        ai_message = OperationChatMessage(
            operation_manual_id=manual_id,
            role="assistant",
            content=result["response"],
            msg_metadata={
                "extracted_context": result.get("extracted_context", {}),
                "is_ready_for_manual": result.get("is_ready_for_manual", False)
            }
        )
        session.add(ai_message)
        session.commit()
        session.refresh(ai_message)
        
        return ChatMessageResponse.model_validate(ai_message)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"チャット応答生成エラー: {str(e)}")


@router.post("/hotels/{hotel_id}/manuals/{manual_id}/generate", response_model=OperationManualResponse)
async def generate_manual(
    hotel_id: int,
    manual_id: int,
    request: GenerateManualRequest = None,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """
    チャット履歴から実行マニュアルを生成
    """
    # マニュアルを取得
    manual = session.get(OperationManual, manual_id)
    if not manual:
        raise HTTPException(status_code=404, detail="オペレーションセッションが見つかりません")
    
    # プランを取得
    plan = session.get(MarketingPlan, manual.marketing_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    # 施設アクセス権確認
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    if not analysis_session or plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=403, detail="このプランへのアクセス権がありません")
    
    # チャット履歴を取得
    messages_statement = select(OperationChatMessage).where(
        OperationChatMessage.operation_manual_id == manual_id
    ).order_by(OperationChatMessage.created_at)
    chat_history = list(session.exec(messages_statement).all())
    
    try:
        # マニュアルを生成
        service = OperationService()
        llm_client = get_llm_client()
        
        additional_instructions = request.additional_instructions if request else None
        
        manual_content = await service.generate_manual(
            manual=manual,
            plan=plan,
            chat_history=chat_history,
            llm_client=llm_client,
            additional_instructions=additional_instructions
        )
        
        # マニュアルを更新
        manual.manual_content = manual_content
        manual.status = OperationManualStatus.completed
        manual.updated_at = datetime.utcnow()
        session.add(manual)
        session.commit()
        session.refresh(manual)
        
        return OperationManualResponse.model_validate(manual)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"マニュアル生成エラー: {str(e)}")


@router.get("/hotels/{hotel_id}/plans/{plan_id}/manual", response_model=OperationManualDetailResponse)
async def get_operation_manual(
    hotel_id: int,
    plan_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_access),
    session: Session = Depends(get_session)
):
    """
    プランのオペレーションマニュアルを取得
    """
    # 施設の分析セッションを取得
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    
    if not analysis_session:
        raise HTTPException(status_code=404, detail="分析セッションが見つかりません")
    
    # プランを取得
    plan = session.get(MarketingPlan, plan_id)
    if not plan or plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    # マニュアルを取得
    statement = select(OperationManual).where(OperationManual.marketing_plan_id == plan_id)
    manual = session.exec(statement).first()
    
    if not manual:
        raise HTTPException(status_code=404, detail="オペレーションマニュアルが見つかりません")
    
    # チャット履歴を取得
    messages_statement = select(OperationChatMessage).where(
        OperationChatMessage.operation_manual_id == manual.id
    ).order_by(OperationChatMessage.created_at)
    messages = session.exec(messages_statement).all()
    
    return OperationManualDetailResponse(
        id=manual.id,
        marketing_plan_id=manual.marketing_plan_id,
        status=manual.status,
        manual_content=manual.manual_content,
        facility_context=manual.facility_context,
        chat_messages=[ChatMessageResponse.model_validate(m) for m in messages],
        created_at=manual.created_at,
        updated_at=manual.updated_at
    )


@router.delete("/hotels/{hotel_id}/manuals/{manual_id}")
async def delete_operation_manual(
    hotel_id: int,
    manual_id: int,
    permission: FacilityAdminHotel = Depends(require_hotel_editor),
    session: Session = Depends(get_session)
):
    """
    オペレーションマニュアルを削除（チャット履歴も含む）
    """
    # マニュアルを取得
    manual = session.get(OperationManual, manual_id)
    if not manual:
        raise HTTPException(status_code=404, detail="オペレーションセッションが見つかりません")
    
    # プランを取得
    plan = session.get(MarketingPlan, manual.marketing_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="プランが見つかりません")
    
    # 施設アクセス権確認
    statement = select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    analysis_session = session.exec(statement).first()
    if not analysis_session or plan.analysis_session_id != analysis_session.id:
        raise HTTPException(status_code=403, detail="このプランへのアクセス権がありません")
    
    # チャット履歴を削除
    messages_statement = select(OperationChatMessage).where(
        OperationChatMessage.operation_manual_id == manual_id
    )
    messages = session.exec(messages_statement).all()
    for msg in messages:
        session.delete(msg)
    
    # マニュアルを削除
    session.delete(manual)
    session.commit()
    
    return {"message": "オペレーションマニュアルを削除しました", "manual_id": manual_id}

