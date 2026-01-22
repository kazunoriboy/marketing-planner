"""Add company model for multi-admin support

Revision ID: 005_add_company_model
Revises: 004_add_csv_upload_history
Create Date: 2026-01-XX

企業グループモデルを追加し、複数の管理者が同じ施設セットにアクセスできるようにする
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005_add_company_model'
down_revision: Union[str, None] = '004_add_csv_upload_history'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """companiesテーブルを作成し、facility_adminsにcompany_idカラムを追加"""
    
    connection = op.get_bind()
    
    # 1. companiesテーブルを作成（存在しない場合のみ）
    table_exists = connection.execute(
        sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'companies')")
    ).scalar()
    
    if not table_exists:
        op.create_table(
            'companies',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 2. facility_adminsにcompany_idカラムを追加（存在しない場合のみ）
    column_exists = connection.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'facility_admins' AND column_name = 'company_id'
            )
        """)
    ).scalar()
    
    if not column_exists:
        op.add_column(
            'facility_admins',
            sa.Column('company_id', sa.Integer(), nullable=True)
        )
        
        # 3. 外部キー制約を追加
        op.create_foreign_key(
            'fk_facility_admins_company_id',
            'facility_admins', 'companies',
            ['company_id'], ['id']
        )
        
        # 4. インデックスを追加
        op.create_index(
            'ix_facility_admins_company_id',
            'facility_admins', ['company_id']
        )
    
    # 既存データはcompany_id=NULLのまま（手動で割り当て可能）


def downgrade() -> None:
    """company_idカラムを削除し、companiesテーブルを削除"""
    
    connection = op.get_bind()
    
    # 1. company_idカラムを削除（存在する場合のみ）
    column_exists = connection.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'facility_admins' AND column_name = 'company_id'
            )
        """)
    ).scalar()
    
    if column_exists:
        # インデックスが存在するかチェック
        index_exists = connection.execute(
            sa.text("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE indexname = 'ix_facility_admins_company_id'
                )
            """)
        ).scalar()
        
        if index_exists:
            op.drop_index('ix_facility_admins_company_id', table_name='facility_admins')
        
        # 外部キー制約を削除
        op.drop_constraint('fk_facility_admins_company_id', 'facility_admins', type_='foreignkey')
        
        op.drop_column('facility_admins', 'company_id')
    
    # 2. companiesテーブルを削除（存在する場合のみ）
    table_exists = connection.execute(
        sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'companies')")
    ).scalar()
    
    if table_exists:
        op.drop_table('companies')
