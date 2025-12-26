"""システムアドミン認証API"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.models import SystemAdmin
from app.auth.jwt import create_access_token, create_refresh_token, verify_token
from app.auth.password import verify_password
from app.auth.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    SystemAdminResponse,
    UserType,
)
from app.auth.dependencies import get_current_system_admin

router = APIRouter(prefix="/admin/auth", tags=["Admin Authentication"])


@router.post("/login", response_model=TokenResponse)
async def admin_login(
    request: LoginRequest,
    session: Session = Depends(get_session)
):
    """
    システムアドミンログイン
    
    - メールアドレスとパスワードで認証
    - 成功時はアクセストークンとリフレッシュトークンを返す
    """
    # ユーザー検索
    admin = session.exec(
        select(SystemAdmin).where(SystemAdmin.email == request.email)
    ).first()
    
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )
    
    # パスワード検証
    if not verify_password(request.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )
    
    # アカウント状態確認
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="アカウントが無効です",
        )
    
    # トークン生成
    access_token = create_access_token(admin.id, UserType.admin)
    refresh_token = create_refresh_token(admin.id, UserType.admin)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def admin_refresh_token(
    request: RefreshTokenRequest,
    session: Session = Depends(get_session)
):
    """
    トークンリフレッシュ
    
    - リフレッシュトークンを使用して新しいアクセストークンを取得
    """
    payload = verify_token(request.refresh_token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なリフレッシュトークンです",
        )
    
    if payload.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="リフレッシュトークンが必要です",
        )
    
    if payload.user_type != UserType.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="システムアドミン用のトークンではありません",
        )
    
    # ユーザー存在確認
    admin = session.exec(
        select(SystemAdmin).where(SystemAdmin.id == payload.user_id)
    ).first()
    
    if admin is None or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つからないか、無効です",
        )
    
    # 新しいトークン生成
    access_token = create_access_token(admin.id, UserType.admin)
    refresh_token = create_refresh_token(admin.id, UserType.admin)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=SystemAdminResponse)
async def get_current_admin(
    admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    現在のアドミン情報を取得
    """
    return SystemAdminResponse(
        id=admin.id,
        email=admin.email,
        name=admin.name,
        is_active=admin.is_active,
    )


