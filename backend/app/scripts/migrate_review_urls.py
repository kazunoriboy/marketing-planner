"""
口コミURL用カラムをhotelsテーブルに追加するマイグレーションスクリプト

実行方法:
    python -m app.scripts.migrate_review_urls
"""
from sqlalchemy import text
from app.core.database import engine


def migrate():
    """review_urlsカラムをhotelsテーブルに追加"""
    with engine.connect() as conn:
        # カラムが存在するか確認
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'hotels' AND column_name = 'review_urls'
        """))
        
        if result.fetchone() is None:
            # カラムが存在しない場合は追加
            conn.execute(text("""
                ALTER TABLE hotels ADD COLUMN review_urls JSON DEFAULT '{}'
            """))
            conn.commit()
            print("✓ review_urlsカラムを追加しました")
        else:
            print("✓ review_urlsカラムは既に存在します")


if __name__ == "__main__":
    migrate()


