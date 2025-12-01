from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # データベース
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/marketing_planner"
    
    # AI API Keys
    GOOGLE_API_KEY: str
    
    # 外部API（将来的に使用）
    MANUS_API_KEY: Optional[str] = None
    V0_API_KEY: Optional[str] = None
    NANO_BANANA_API_KEY: Optional[str] = None
    
    # アプリケーション設定
    APP_NAME: str = "Marketing Planner API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # CORS設定
    CORS_ORIGINS: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


