-- 既存プランテーブルの作成
-- 宿が現在運用しているプランを登録し、見せ方を変えたマーケティングプランを生成するために使用

CREATE TABLE IF NOT EXISTS existing_plans (
    id SERIAL PRIMARY KEY,
    hotel_id INTEGER NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    
    -- プラン基本情報
    plan_title VARCHAR(255) NOT NULL,
    plan_description TEXT NOT NULL,
    
    -- 部屋についている施設・設備（JSON配列）
    -- 例: ["露天風呂", "マッサージチェア", "ミニバー"]
    room_facilities JSONB DEFAULT '[]',
    
    -- 宿自体の活用可能な資産（JSON配列）
    -- 例: ["大浴場", "貸切風呂", "レストラン", "庭園"]
    hotel_assets JSONB DEFAULT '[]',
    
    -- 現在の価格帯（参考情報）
    -- {"min": 10000, "max": 30000, "standard": 20000}
    price_info JSONB DEFAULT '{}',
    
    -- 食事に関する情報
    -- {"breakfast": "和洋バイキング", "dinner": "会席料理", "options": ["部屋食可"]}
    meal_info JSONB DEFAULT '{}',
    
    -- その他特記事項
    notes TEXT,
    
    -- メタデータ
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_existing_plans_hotel_id ON existing_plans(hotel_id);
CREATE INDEX IF NOT EXISTS idx_existing_plans_is_active ON existing_plans(is_active);



