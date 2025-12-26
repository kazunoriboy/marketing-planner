"""JWT生成・検証モジュール"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt

from app.core.config import settings
from app.auth.schemas import UserType, TokenPayload


def create_access_token(
    user_id: int,
    user_type: UserType,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    アクセストークンを生成
    
    Args:
        user_id: ユーザーID
        user_type: ユーザータイプ（admin/facility）
        expires_delta: 有効期限（デフォルト: 設定値）
    
    Returns:
        JWTトークン文字列
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "sub": str(user_id),
        "type": user_type.value,
        "token_type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    user_id: int,
    user_type: UserType,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    リフレッシュトークンを生成
    
    Args:
        user_id: ユーザーID
        user_type: ユーザータイプ（admin/facility）
        expires_delta: 有効期限（デフォルト: 設定値）
    
    Returns:
        JWTトークン文字列
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode = {
        "sub": str(user_id),
        "type": user_type.value,
        "token_type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenPayload]:
    """
    トークンを検証してペイロードを返す
    
    Args:
        token: JWTトークン文字列
    
    Returns:
        トークンペイロード（無効な場合はNone）
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id = payload.get("sub")
        user_type = payload.get("type")
        token_type = payload.get("token_type")
        exp = payload.get("exp")
        
        if user_id is None or user_type is None:
            return None
        
        return TokenPayload(
            user_id=int(user_id),
            user_type=UserType(user_type),
            token_type=token_type,
            exp=exp
        )
    except JWTError:
        return None


