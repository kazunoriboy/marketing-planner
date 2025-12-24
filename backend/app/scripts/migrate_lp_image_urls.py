"""
lp_image_urlsカラムをcreative_assetsテーブルに追加するマイグレーションスクリプト

実行方法:
    docker compose exec backend python -m app.scripts.migrate_lp_image_urls
"""

import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.core.database import engine


def migrate():
    """lp_image_urlsカラムを追加"""
    with engine.connect() as conn:
        # カラムが存在するか確認
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'creative_assets' AND column_name = 'lp_image_urls'
        """))
        
        if result.fetchone() is None:
            # カラムを追加（JSONタイプ、デフォルトは空のJSON）
            conn.execute(text("""
                ALTER TABLE creative_assets ADD COLUMN lp_image_urls JSON DEFAULT '{}'
            """))
            conn.commit()
            print("✅ lp_image_urls カラムを追加しました")
        else:
            print("ℹ️ lp_image_urls カラムは既に存在します")


if __name__ == "__main__":
    print("🔄 マイグレーションを実行中...")
    migrate()
    print("✅ マイグレーション完了")

