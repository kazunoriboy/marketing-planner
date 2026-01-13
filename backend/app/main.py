import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import traceback

from app.core.database import create_db_and_tables
from app.core.config import settings
from app.api import analysis, planning, creative, operation
from app.api import admin_auth, admin_users, facility_auth, facility_hotels

# ロギング設定
def setup_logging():
    """ログ設定を初期化"""
    # ログディレクトリを作成
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルパス
    log_file = os.path.join(log_dir, "app.log")
    error_log_file = os.path.join(log_dir, "error.log")
    
    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラー（通常ログ）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # ファイルハンドラー（エラーログ）
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    return logging.getLogger(__name__)

# ロガーを初期化
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時: データベースとテーブルを作成
    print("🚀 Starting up...")
    print("📊 Creating database tables...")
    create_db_and_tables()
    print("✅ Database tables created successfully")
    
    yield
    
    # 終了時の処理（必要に応じて追加）
    print("👋 Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="宿泊施設向けマーケティングAIエージェント API",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 例外ハンドリングミドルウェア
@app.middleware("http")
async def log_exceptions_middleware(request: Request, call_next):
    """リクエストの例外をログに記録"""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(f"Request: {request.method} {request.url}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise

# 静的ファイル配信（生成画像用）
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# APIルーターの登録（既存）
app.include_router(analysis.router)
app.include_router(planning.router)
app.include_router(creative.router)
app.include_router(operation.router)

# APIルーターの登録（認証関連）
app.include_router(admin_auth.router)
app.include_router(admin_users.router)
app.include_router(facility_auth.router)
app.include_router(facility_hotels.router)


@app.get("/")
async def root():
    return {
        "message": "Hello from FastAPI Backend - 宿泊業界向けマーケティングAIエージェント",
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "marketing-planner-api",
        "version": settings.APP_VERSION
    }


@app.get("/api/test")
async def test_endpoint():
    return {
        "message": "API接続テスト成功",
        "features": [
            "宿泊施設登録・管理",
            "顧客データ分析（CSV）",
            "市場調査・競合分析",
            "マーケティングプラン生成（3C・PEST分析）",
            "クリエイティブアセット生成（LP・広告コピー・画像プロンプト）"
        ],
        "ai_models": [
            "Claude 3.5 Sonnet (Anthropic)"
        ]
    }
