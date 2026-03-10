"""Add hotel_detail column to hotels

Revision ID: 007_add_hotel_detail
Revises: 006_add_facility_images
Create Date: 2026-03-04

宿のストーリー・周辺情報を保持する hotel_detail カラムを hotels テーブルに追加
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007_add_hotel_detail'
down_revision: Union[str, None] = '006_add_facility_images'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """hotelsテーブルに hotel_detail カラムを追加（既存の場合はスキップ）"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'hotels' AND column_name = 'hotel_detail'"
        )
    ).scalar()
    if result is None:
        op.add_column(
            'hotels',
            sa.Column('hotel_detail', postgresql.JSONB(), nullable=True, server_default='{}')
        )


def downgrade() -> None:
    """hotel_detail カラムを削除（存在する場合のみ）"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'hotels' AND column_name = 'hotel_detail'"
        )
    ).scalar()
    if result is not None:
        op.drop_column('hotels', 'hotel_detail')
