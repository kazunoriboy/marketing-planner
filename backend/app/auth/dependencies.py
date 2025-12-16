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


def get_hotel_access_checker(required_roles: Optional[list[str]] = None):
    """
    施設アクセス権限チェック依存関数を生成するファクトリ関数
    
    Args:
        required_roles: 必要な権限のリスト。Noneの場合は全ての権限（owner, editor, viewer）を許可
    
    Returns:
        依存関数
    
    Usage:
        @router.get("/hotels/{hotel_id}/data")
        async def get_hotel_data(
            hotel_id: int,
            permission: FacilityAdminHotel = Depends(get_hotel_access_checker())
        ):
            # permissionには権限情報が含まれる
            pass
        
        # 特定の権限が必要な場合
        @router.post("/hotels/{hotel_id}/data")
        async def update_hotel_data(
            hotel_id: int,
            permission: FacilityAdminHotel = Depends(get_hotel_access_checker(["owner", "editor"]))
        ):
            pass
    """
    # 遅延インポートで循環参照を回避
    from app.models import FacilityAdminHotel, FacilityAdminHotelRole
    
    # デフォルトは全ての権限を許可
    if required_roles is None:
        required_roles = [
            FacilityAdminHotelRole.owner.value,
            FacilityAdminHotelRole.editor.value,
            FacilityAdminHotelRole.viewer.value,
        ]
    
    async def require_hotel_access(
        hotel_id: int,
        facility_admin = Depends(get_current_facility_admin),
        session: Session = Depends(get_session)
    ) -> FacilityAdminHotel:
        """
        施設へのアクセス権限をチェックする依存関数
        
        Args:
            hotel_id: 施設ID（パスパラメータから自動取得）
            facility_admin: 現在の施設管理者
            session: データベースセッション
        
        Returns:
            FacilityAdminHotel: 権限情報
        
        Raises:
            HTTPException: 権限がない場合は403 Forbidden
        """
        permission = session.exec(
            select(FacilityAdminHotel).where(
                FacilityAdminHotel.facility_admin_id == facility_admin.id,
                FacilityAdminHotel.hotel_id == hotel_id
            )
        ).first()
        
        if permission is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この施設へのアクセス権限がありません",
            )
        
        if permission.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"この操作には {', '.join(required_roles)} のいずれかの権限が必要です",
            )
        
        return permission
    
    return require_hotel_access


# よく使う権限チェッカーのショートカット
require_hotel_access = get_hotel_access_checker()  # 全ての権限を許可
require_hotel_editor = get_hotel_access_checker(["owner", "editor"])  # 編集者以上
require_hotel_owner = get_hotel_access_checker(["owner"])  # オーナーのみ
