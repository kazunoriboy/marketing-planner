-- creative_assetsテーブルにota_textカラムを追加するマイグレーション
-- 実行方法: psql -d marketing_planner -f add_ota_text_column.sql

-- ota_textカラムを追加（存在しない場合のみ）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'creative_assets' AND column_name = 'ota_text'
    ) THEN
        ALTER TABLE creative_assets ADD COLUMN ota_text JSONB DEFAULT '{}';
        RAISE NOTICE 'ota_text column added successfully';
    ELSE
        RAISE NOTICE 'ota_text column already exists';
    END IF;
END $$;


