"""Add ota_text column to creative_assets

Revision ID: 002_add_ota_text
Revises: 001_initial
Create Date: 2026-01-04

OTA（じゃらん、楽天トラベル）向けテキスト保存用カラムを追加
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_ota_text'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """creative_assetsテーブルにota_textカラムを追加"""
    # カラムが存在しない場合のみ追加
    op.add_column(
        'creative_assets',
        sa.Column('ota_text', postgresql.JSONB(), nullable=True, server_default='{}')
    )


def downgrade() -> None:
    """ota_textカラムを削除"""
    op.drop_column('creative_assets', 'ota_text')

