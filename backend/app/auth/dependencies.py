"""認証依存関係モジュール"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from app.core.database import get_session
from app.auth.jwt import verify_token
from app.auth.schemas import UserType, TokenPayload

# Bearer tokenスキーム
security = HTTPBearer()


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenPayload:
    """
    トークンからペイロードを取得
    
    Raises:
        HTTPException: 無効なトークンの場合
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if payload.token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="アクセストークンが必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def get_current_system_admin(
    payload: TokenPayload = Depends(get_token_payload),
    session: Session = Depends(get_session)
):
    """
    現在のシステムアドミンを取得
    
    Raises:
        HTTPException: 権限がない場合
    """
    # 遅延インポートで循環参照を回避
    from app.models import SystemAdmin
    
    if payload.user_type != UserType.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="システムアドミン権限が必要です",
        )
    
    admin = session.exec(
        select(SystemAdmin).where(SystemAdmin.id == payload.user_id)
    ).first()
    
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="アドミンが見つかりません",
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="アカウントが無効です",
        )
    
    return admin


async def get_current_facility_admin(
    payload: TokenPayload = Depends(get_token_payload),
    session: Session = Depends(get_session)
):
    """
    現在の施設管理者を取得
    
    Raises:
        HTTPException: 権限がない場合
    """
    # 遅延インポートで循環参照を回避
    from app.models import FacilityAdmin
    
    if payload.user_type != UserType.facility:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="施設管理者権限が必要です",
        )
    
    facility_admin = session.exec(
        select(FacilityAdmin).where(FacilityAdmin.id == payload.user_id)
    ).first()
    
    if facility_admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設管理者が見つかりません",
        )
    
    if not facility_admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="アカウントが無効です",
        )
    
    return facility_admin


def check_hotel_permission(
    facility_admin_id: int,
    hotel_id: int,
    required_roles: list[str],
    session: Session
) -> bool:
    """
    施設管理者が特定の施設に対する権限を持っているか確認
    
    Args:
        facility_admin_id: 施設管理者ID
        hotel_id: 施設ID
        required_roles: 必要な権限のリスト
        session: データベースセッション
    
    Returns:
        権限がある場合True
    """
    # 遅延インポートで循環参照を回避
    from app.models import FacilityAdminHotel
    
    permission = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin_id,
            FacilityAdminHotel.hotel_id == hotel_id
        )
    ).first()
    
    if permission is None:
        return False
    
    return permission.role in required_roles
