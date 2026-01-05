"""Initial baseline - existing database schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-04

このマイグレーションは既存のDBスキーマをベースラインとしてマークするものです。
実際のテーブル作成は行いません（既に存在するため）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    既存のテーブル構造をベースラインとしてマーク
    このマイグレーションでは何も作成しない（既に存在するため）
    
    既存テーブル:
    - system_admins
    - facility_admins
    - facility_admin_hotels
    - hotels
    - analysis_sessions
    - marketing_plans
    - creative_assets
    - operation_manuals
    - operation_chat_messages
    - existing_plans
    """
    pass


def downgrade() -> None:
    """ベースラインなのでダウングレードは不要"""
    pass

