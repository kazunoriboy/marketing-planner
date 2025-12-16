"""施設管理者認証API"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.database import get_session
from app.models import FacilityAdmin, FacilityAdminHotel, Hotel
from app.auth.jwt import create_access_token, create_refresh_token, verify_token
from app.auth.password import verify_password, hash_password, validate_password_strength
from app.auth.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    FacilityAdminResponse,
    PasswordChangeRequest,
    UserType,
)
from app.auth.dependencies import get_current_facility_admin

router = APIRouter(prefix="/facility/auth", tags=["Facility Authentication"])


class FacilityAdminMeResponse(FacilityAdminResponse):
    """現在の施設管理者レスポンス（施設情報含む）"""
    hotels: List[dict] = []


@router.post("/login", response_model=TokenResponse)
async def facility_login(
    request: LoginRequest,
    session: Session = Depends(get_session)
):
    """
    施設管理者ログイン
    
    - メールアドレスとパスワードで認証
    - 成功時はアクセストークンとリフレッシュトークンを返す
    """
    # ユーザー検索
    facility_admin = session.exec(
        select(FacilityAdmin).where(FacilityAdmin.email == request.email)
    ).first()
    
    if facility_admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )
    
    # パスワード検証
    if not verify_password(request.password, facility_admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )
    
    # アカウント状態確認
    if not facility_admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="アカウントが無効です",
        )
    
    # トークン生成
    access_token = create_access_token(facility_admin.id, UserType.facility)
    refresh_token = create_refresh_token(facility_admin.id, UserType.facility)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def facility_refresh_token(
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
    
    if payload.user_type != UserType.facility:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="施設管理者用のトークンではありません",
        )
    
    # ユーザー存在確認
    facility_admin = session.exec(
        select(FacilityAdmin).where(FacilityAdmin.id == payload.user_id)
    ).first()
    
    if facility_admin is None or not facility_admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つからないか、無効です",
        )
    
    # 新しいトークン生成
    access_token = create_access_token(facility_admin.id, UserType.facility)
    refresh_token = create_refresh_token(facility_admin.id, UserType.facility)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=FacilityAdminMeResponse)
async def get_current_facility_admin_me(
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    現在の施設管理者情報を取得
    
    - 紐付けられた施設情報も含む
    """
    # 紐付けられた施設を取得
    permissions = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id
        )
    ).all()
    
    hotels = []
    for perm in permissions:
        hotel = session.exec(
            select(Hotel).where(Hotel.id == perm.hotel_id)
        ).first()
        if hotel:
            hotels.append({
                "id": hotel.id,
                "name": hotel.name,
                "address": hotel.address,
                "role": perm.role,
            })
    
    return FacilityAdminMeResponse(
        id=facility_admin.id,
        email=facility_admin.email,
        name=facility_admin.name,
        is_active=facility_admin.is_active,
        hotels=hotels,
    )


@router.put("/password")
async def change_password(
    request: PasswordChangeRequest,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    パスワード変更
    
    - 現在のパスワードを検証
    - 新しいパスワードは強度ポリシーに従う必要がある
    """
    # 現在のパスワードを検証
    if not verify_password(request.current_password, facility_admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在のパスワードが正しくありません",
        )
    
    # 新しいパスワードをハッシュ化して保存
    facility_admin.password_hash = hash_password(request.new_password)
    facility_admin.updated_at = datetime.utcnow()
    
    session.add(facility_admin)
    session.commit()
    
    return {"message": "パスワードを変更しました"}
