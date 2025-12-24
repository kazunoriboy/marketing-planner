"""認証関連スキーマ"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator

from app.auth.password import validate_password_strength


class UserType(str, Enum):
    """ユーザータイプ"""
    admin = "admin"
    facility = "facility"


class LoginRequest(BaseModel):
    """ログインリクエスト"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """トークンレスポンス"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """トークンペイロード"""
    user_id: int
    user_type: UserType
    token_type: str
    exp: int


class RefreshTokenRequest(BaseModel):
    """リフレッシュトークンリクエスト"""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """パスワード変更リクエスト"""
    current_password: str
    new_password: str
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v


class SystemAdminResponse(BaseModel):
    """システムアドミンレスポンス"""
    id: int
    email: str
    name: str
    is_active: bool
    
    class Config:
        from_attributes = True


class FacilityAdminResponse(BaseModel):
    """施設管理者レスポンス"""
    id: int
    email: str
    name: str
    is_active: bool
    
    class Config:
        from_attributes = True


class FacilityAdminCreateRequest(BaseModel):
    """施設管理者作成リクエスト"""
    email: EmailStr
    name: str
    password: str
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v


class FacilityAdminUpdateRequest(BaseModel):
    """施設管理者更新リクエスト"""
    name: Optional[str] = None
    is_active: Optional[bool] = None


class FacilityAdminHotelRole(str, Enum):
    """施設管理者の施設に対する権限"""
    owner = "owner"      # オーナー（全権限）
    editor = "editor"    # 編集者（編集権限）
    viewer = "viewer"    # 閲覧者（閲覧のみ）


class FacilityAdminHotelResponse(BaseModel):
    """施設管理者-施設紐付けレスポンス"""
    id: int
    facility_admin_id: int
    hotel_id: int
    role: FacilityAdminHotelRole
    
    class Config:
        from_attributes = True

