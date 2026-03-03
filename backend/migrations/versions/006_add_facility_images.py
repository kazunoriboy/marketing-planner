"""Add facility_images column to hotels

Revision ID: 006_add_facility_images
Revises: 005_add_company_model
Create Date: 2026-02-11

施設画像をJSON配列で保持するfacility_imagesカラムを追加
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_add_facility_images'
down_revision: Union[str, None] = '005_add_company_model'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """hotelsテーブルにfacility_imagesカラムを追加（既存の場合はスキップ）"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'hotels' AND column_name = 'facility_images'"
        )
    ).scalar()
    if result is None:
        op.add_column(
            'hotels',
            sa.Column('facility_images', postgresql.JSONB(), nullable=True, server_default='[]')
        )


def downgrade() -> None:
    """facility_imagesカラムを削除（存在する場合のみ）"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'hotels' AND column_name = 'facility_images'"
        )
    ).scalar()
    if result is not None:
        op.drop_column('hotels', 'facility_images')
