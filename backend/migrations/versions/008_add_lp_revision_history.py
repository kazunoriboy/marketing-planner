"""Add lp_revision_history column to creative_assets

Revision ID: 008_add_lp_revision_history
Revises: 007_add_hotel_detail
Create Date: 2026-03-10

LP調整機能のための修正履歴カラムを creative_assets テーブルに追加
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_add_lp_revision_history'
down_revision: Union[str, None] = '007_add_hotel_detail'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """creative_assetsテーブルに lp_revision_history カラムを追加（既存の場合はスキップ）"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'creative_assets' AND column_name = 'lp_revision_history'"
        )
    ).scalar()
    if result is None:
        op.add_column(
            'creative_assets',
            sa.Column('lp_revision_history', postgresql.JSONB(), nullable=True, server_default='[]')
        )


def downgrade() -> None:
    """lp_revision_history カラムを削除（存在する場合のみ）"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'creative_assets' AND column_name = 'lp_revision_history'"
        )
    ).scalar()
    if result is not None:
        op.drop_column('creative_assets', 'lp_revision_history')
