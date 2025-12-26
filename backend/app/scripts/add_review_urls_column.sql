-- 口コミURL用カラムをhotelsテーブルに追加するマイグレーション
-- 実行方法: psql -d marketing_planner -f add_review_urls_column.sql

-- カラムが存在しない場合のみ追加
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'hotels' AND column_name = 'review_urls'
    ) THEN
        ALTER TABLE hotels ADD COLUMN review_urls JSON DEFAULT '{}';
    END IF;
END $$;


