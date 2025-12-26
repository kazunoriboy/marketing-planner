from pydantic import BaseModel, field_validator
from typing import Dict, List, Optional
from datetime import datetime
from app.models import OperationManualStatus


class ChatMessageRequest(BaseModel):
    """チャットメッセージリクエスト"""
    message: str
    
    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("メッセージを入力してください")
        return v.strip()


class ChatMessageResponse(BaseModel):
    """チャットメッセージレスポンス"""
    id: int
    operation_manual_id: int
    role: str  # "user" or "assistant"
    content: str
    msg_metadata: Dict
    created_at: datetime
    
    class Config:
        from_attributes = True


class OperationManualResponse(BaseModel):
    """オペレーションマニュアルレスポンス"""
    id: int
    marketing_plan_id: int
    status: OperationManualStatus
    manual_content: Dict
    facility_context: Dict
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OperationManualDetailResponse(BaseModel):
    """オペレーションマニュアル詳細レスポンス（チャット履歴含む）"""
    id: int
    marketing_plan_id: int
    status: OperationManualStatus
    manual_content: Dict
    facility_context: Dict
    chat_messages: List[ChatMessageResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GenerateManualRequest(BaseModel):
    """マニュアル生成リクエスト"""
    # 追加の指示があれば
    additional_instructions: Optional[str] = None


class ManualTaskResponse(BaseModel):
    """マニュアルタスクレスポンス（フロントエンド表示用）"""
    title: str
    description: str
    estimated_time: Optional[str] = None
    responsible: Optional[str] = None
    tools: Optional[List[str]] = None


class ManualPhaseResponse(BaseModel):
    """マニュアルフェーズレスポンス"""
    name: str
    description: Optional[str] = None
    tasks: List[ManualTaskResponse]


class ManualContentResponse(BaseModel):
    """マニュアル内容レスポンス（構造化）"""
    title: str
    overview: str
    phases: List[ManualPhaseResponse]
    timeline: Optional[str] = None
    budget_estimate: Optional[str] = None
    success_metrics: Optional[List[str]] = None
    notes: Optional[str] = None

