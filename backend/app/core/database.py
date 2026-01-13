from sqlmodel import create_engine, SQLModel, Session
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# データベース接続URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/marketing_planner"
)

# エンジンの作成
engine = create_engine(
    DATABASE_URL,
    echo=False,  # True: SQLログを出力（デバッグ用）
    pool_pre_ping=True,  # 接続の健全性チェック
    pool_size=10,  # 接続プールのサイズ
    max_overflow=20,  # プールが満杯の場合の追加接続数
    pool_timeout=30,  # 接続取得のタイムアウト（秒）
)


def create_db_and_tables():
    """データベースとテーブルを作成"""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """データベースセッションを取得（依存性注入用）"""
    with Session(engine) as session:
        yield session


