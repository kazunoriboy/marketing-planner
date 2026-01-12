"""Add personas column to analysis_sessions

Revision ID: 003_add_personas
Revises: 002_add_ota_text
Create Date: 2026-01-12

ペルソナ（顧客像）をJSON配列として保存するカラムを追加
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_add_personas'
down_revision: Union[str, None] = '002_add_ota_text'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """analysis_sessionsテーブルにpersonasカラムを追加"""
    op.add_column(
        'analysis_sessions',
        sa.Column('personas', postgresql.JSONB(), nullable=True, server_default='[]')
    )


def downgrade() -> None:
    """personasカラムを削除"""
    op.drop_column('analysis_sessions', 'personas')
