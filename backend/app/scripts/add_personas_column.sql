-- analysis_sessionsテーブルにpersonasカラムを追加
-- ペルソナ（顧客像）をJSON配列として保存

ALTER TABLE analysis_sessions
ADD COLUMN IF NOT EXISTS personas JSON DEFAULT '[]';

-- 確認用クエリ
-- SELECT id, hotel_id, personas FROM analysis_sessions;

