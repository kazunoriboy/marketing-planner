from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Marketing Planner API", version="1.0.0")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI Backend - 宿泊業界向けマーケティングAIエージェント"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "marketing-planner-api"}

@app.get("/api/test")
async def test_endpoint():
    return {
        "message": "API接続テスト成功",
        "timestamp": "2024-09-12T16:00:00Z",
        "features": [
            "宿泊業界向けマーケティング分析",
            "AI エージェント機能",
            "RAG (Retrieval-Augmented Generation)",
            "ベクトル検索"
        ]
    }
