"""Alembic環境設定"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# プロジェクトのルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# モデルをインポート（SQLModelのmetadataを取得するため）
from app.models import *  # noqa
from sqlmodel import SQLModel

# Alembic Config オブジェクト
config = context.config

# ログ設定
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# メタデータの設定（オートジェネレート用）
target_metadata = SQLModel.metadata

# データベースURL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/marketing_planner"
)


def run_migrations_offline() -> None:
    """オフラインモードでマイグレーション実行（SQL生成のみ）"""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """オンラインモードでマイグレーション実行"""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = DATABASE_URL
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # カラム型の変更を検出
            compare_server_default=True,  # デフォルト値の変更を検出
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

