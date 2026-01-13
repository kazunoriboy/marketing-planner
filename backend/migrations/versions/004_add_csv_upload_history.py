"""Add CSV upload history table

Revision ID: 004_add_csv_upload_history
Revises: 003_add_personas
Create Date: 2026-01-13

CSVアップロード履歴テーブルを追加し、過去の分析を保持・合算できるようにする
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_add_csv_upload_history'
down_revision: Union[str, None] = '003_add_personas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """CSVUploadHistoryテーブルを作成し、AnalysisSessionにcsv_upload_countを追加"""
    
    # 接続を取得してテーブルの存在をチェック
    connection = op.get_bind()
    
    # 1. csv_upload_histories テーブルを作成（存在しない場合のみ）
    table_exists = connection.execute(
        sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'csv_upload_histories')")
    ).scalar()
    
    if not table_exists:
        op.create_table(
            'csv_upload_histories',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('hotel_id', sa.Integer(), nullable=False),
            sa.Column('filename', sa.String(), nullable=False),
            sa.Column('file_hash', sa.String(), nullable=True),
            sa.Column('data_period_start', sa.DateTime(), nullable=True),
            sa.Column('data_period_end', sa.DateTime(), nullable=True),
            sa.Column('statistics', postgresql.JSONB(), nullable=True, server_default='{}'),
            sa.Column('record_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_migrated', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('notes', sa.String(), nullable=True),
            sa.Column('upload_date', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['hotel_id'], ['hotels.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_csv_upload_histories_hotel_id'), 'csv_upload_histories', ['hotel_id'], unique=False)
    
    # 2. analysis_sessions に csv_upload_count カラムを追加（存在しない場合のみ）
    column_exists = connection.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'analysis_sessions' AND column_name = 'csv_upload_count'
            )
        """)
    ).scalar()
    
    if not column_exists:
        op.add_column(
            'analysis_sessions',
            sa.Column('csv_upload_count', sa.Integer(), nullable=False, server_default='0')
        )
    
    # 3. 既存データの移行: csv_statisticsが空でないセッションをCSVUploadHistoryに移行
    # 既に移行済みのデータがあるかチェック
    migrated_exists = connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM csv_upload_histories WHERE is_migrated = true LIMIT 1)")
    ).scalar()
    
    if not migrated_exists:
        # SQLで直接実行（csv_statisticsがJSON型の場合はキャストが必要）
        op.execute("""
            INSERT INTO csv_upload_histories (hotel_id, filename, statistics, record_count, is_migrated, notes, upload_date, created_at)
            SELECT 
                hotel_id,
                '移行データ（過去分）',
                csv_statistics::jsonb,
                COALESCE((csv_statistics->>'total_records')::integer, 0),
                true,
                'システム移行により自動作成',
                created_at,
                NOW()
            FROM analysis_sessions
            WHERE csv_statistics IS NOT NULL 
              AND csv_statistics::text NOT IN ('{}', 'null', '')
        """)
        
        # 4. 移行したセッションの csv_upload_count を 1 に更新
        op.execute("""
            UPDATE analysis_sessions
            SET csv_upload_count = 1
            WHERE csv_statistics IS NOT NULL 
              AND csv_statistics::text NOT IN ('{}', 'null', '')
        """)


def downgrade() -> None:
    """CSVUploadHistoryテーブルを削除し、csv_upload_countカラムを削除"""
    
    connection = op.get_bind()
    
    # 1. csv_upload_count カラムを削除（存在する場合のみ）
    column_exists = connection.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'analysis_sessions' AND column_name = 'csv_upload_count'
            )
        """)
    ).scalar()
    
    if column_exists:
        op.drop_column('analysis_sessions', 'csv_upload_count')
    
    # 2. csv_upload_histories テーブルを削除（存在する場合のみ）
    table_exists = connection.execute(
        sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'csv_upload_histories')")
    ).scalar()
    
    if table_exists:
        # インデックスが存在するかチェック
        index_exists = connection.execute(
            sa.text("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE indexname = 'ix_csv_upload_histories_hotel_id'
                )
            """)
        ).scalar()
        
        if index_exists:
            op.drop_index(op.f('ix_csv_upload_histories_hotel_id'), table_name='csv_upload_histories')
        
        op.drop_table('csv_upload_histories')
