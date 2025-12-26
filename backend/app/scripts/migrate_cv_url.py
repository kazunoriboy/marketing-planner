"""
cv_urlカラムをhotelsテーブルに追加するマイグレーションスクリプト

実行方法:
    docker compose exec backend python -m app.scripts.migrate_cv_url
"""

import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.core.database import engine


def migrate():
    """cv_urlカラムを追加"""
    with engine.connect() as conn:
        # カラムが存在するか確認
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'hotels' AND column_name = 'cv_url'
        """))
        
        if result.fetchone() is None:
            # カラムを追加
            conn.execute(text("""
                ALTER TABLE hotels ADD COLUMN cv_url VARCHAR(500) DEFAULT NULL
            """))
            conn.commit()
            print("✅ cv_url カラムを追加しました")
        else:
            print("ℹ️ cv_url カラムは既に存在します")


if __name__ == "__main__":
    print("🔄 マイグレーションを実行中...")
    migrate()
    print("✅ マイグレーション完了")


