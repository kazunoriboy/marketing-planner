-- hotelsテーブルにcv_urlカラムを追加するマイグレーション
-- 実行方法: psql -d marketing_planner -f add_cv_url_column.sql

-- cv_urlカラムを追加（存在しない場合のみ）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'hotels' AND column_name = 'cv_url'
    ) THEN
        ALTER TABLE hotels ADD COLUMN cv_url VARCHAR(500) DEFAULT NULL;
        RAISE NOTICE 'cv_url column added successfully';
    ELSE
        RAISE NOTICE 'cv_url column already exists';
    END IF;
END $$;

