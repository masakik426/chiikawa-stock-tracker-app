-- ちいかわグッズ 在庫・発売情報まとめサイト
-- Supabase の SQL エディタにこの内容を貼り付けて実行してください

-- 商品マスタ
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,           -- 商品名
    category VARCHAR(100),                -- カテゴリ（ぬいぐるみ/ガチャ/食玩/コラボ/その他）
    official_release_date DATE,           -- 公式発売日
    official_price INTEGER,               -- 定価（円）
    official_site_url TEXT,               -- 公式サイトURL
    image_url TEXT,                       -- 商品画像URL
    affiliate_amazon TEXT,                -- Amazon アフィリエイトURL
    affiliate_rakuten TEXT,               -- 楽天 アフィリエイトURL
    notes TEXT,                           -- 備考
    created_at TIMESTAMP DEFAULT NOW()
);

-- 店舗マスタ
CREATE TABLE stores (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,           -- 店舗名
    store_type VARCHAR(100),              -- 店舗種別（100均/コンビニ/百貨店/EC/その他）
    region VARCHAR(100),                  -- 地域（都道府県）
    address TEXT,                         -- 住所
    latitude FLOAT,                       -- 緯度（マップ表示用）
    longitude FLOAT,                      -- 経度（マップ表示用）
    website_url TEXT,                     -- 公式サイトURL
    x_account VARCHAR(100),              -- Xアカウント名
    created_at TIMESTAMP DEFAULT NOW()
);

-- 在庫報告
CREATE TABLE inventory_reports (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,          -- in_stock / out_of_stock / limited
    source VARCHAR(50),                   -- x_mention / x_hashtag / x_official / web_form
    x_post_url TEXT,                      -- 元Xポストへのリンク
    x_post_date TIMESTAMP,                -- Xポストの投稿日時
    reporter_x_id VARCHAR(100),           -- 報告者のXアカウントID
    created_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE      -- 削除フラグ
);

-- 発売スケジュール
CREATE TABLE release_schedule (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE,  -- NULL = 全国発売
    scheduled_date DATE NOT NULL,         -- 発売予定日
    is_confirmed BOOLEAN DEFAULT FALSE,   -- 発売確定かどうか
    notes TEXT,                           -- 備考（ポップアップ限定 等）
    created_at TIMESTAMP DEFAULT NOW()
);

-- カテゴリ別の色設定（参考）
-- ぬいぐるみ  → #FF69B4（ピンク）
-- ガチャ      → #4169E1（ブルー）
-- 食玩        → #FF8C00（オレンジ）
-- コラボ      → #9370DB（パープル）
-- その他      → #20B2AA（ティール）
