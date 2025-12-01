from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import create_db_and_tables
from app.core.config import settings
from app.api import analysis, planning, creative


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

# APIルーターの登録
app.include_router(analysis.router)
app.include_router(planning.router)
app.include_router(creative.router)


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
