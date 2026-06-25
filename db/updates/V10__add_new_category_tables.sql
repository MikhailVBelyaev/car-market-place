-- V10: New marketplace categories — real estate (apartments/houses) and
-- electronics (GPUs + Apple products). Mirrors the conventions used by the
-- existing marketplace.cars table: a string ad_id sourced from the OLX URL,
-- a scraped_at audit column, and TEXT[]/JSONB for flexible scraped data.
--
-- Flyway owns the schema; the Django ORM models for these tables use
-- managed = False (same as marketplace.cars).

-- ---------------------------------------------------------------------------
-- Real estate listings (apartments + houses)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marketplace.apartments (
    ad_id          VARCHAR(50)  PRIMARY KEY,
    title          TEXT,
    price          NUMERIC(14, 2),
    price_currency VARCHAR(10),            -- 'USD' or 'UZS'
    area_m2        NUMERIC(10, 2),
    rooms          INT,
    floor          INT,
    total_floors   INT,
    district       VARCHAR(255),
    address        TEXT,
    condition      VARCHAR(50),            -- new / renovation / old
    property_type  VARCHAR(50),            -- apartment / house / etc
    description    TEXT,
    seller_name    VARCHAR(255),
    seller_phone   VARCHAR(50),
    url            TEXT,
    images         TEXT[],
    created_at     TIMESTAMP,              -- when the ad was posted on OLX
    scraped_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_apartments_property_type ON marketplace.apartments (property_type);
CREATE INDEX IF NOT EXISTS idx_apartments_district      ON marketplace.apartments (district);
CREATE INDEX IF NOT EXISTS idx_apartments_created_at    ON marketplace.apartments (created_at);

-- ---------------------------------------------------------------------------
-- Electronics listings (video cards + Apple products)
-- specs is JSONB so each category can carry its own attributes:
--   gpu     -> {"memory_gb": 8, "gpu_series": "RTX 3070"}
--   iphone  -> {"storage_gb": 256, "color": "black"}
--   macbook -> {"ram_gb": 16, "storage_gb": 512, "chip": "M2"}
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marketplace.electronics (
    ad_id          VARCHAR(50)  PRIMARY KEY,
    category       VARCHAR(20),            -- gpu / iphone / macbook / ipad / airpods
    title          TEXT,
    brand          VARCHAR(100),
    model          VARCHAR(255),
    price          NUMERIC(14, 2),
    price_currency VARCHAR(10),            -- 'USD' or 'UZS'
    condition      VARCHAR(20),            -- new / used
    description    TEXT,
    seller_name    VARCHAR(255),
    seller_phone   VARCHAR(50),
    url            TEXT,
    images         TEXT[],
    specs          JSONB,
    created_at     TIMESTAMP,
    scraped_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_electronics_category   ON marketplace.electronics (category);
CREATE INDEX IF NOT EXISTS idx_electronics_brand      ON marketplace.electronics (brand);
CREATE INDEX IF NOT EXISTS idx_electronics_created_at ON marketplace.electronics (created_at);

GRANT ALL PRIVILEGES ON marketplace.apartments  TO marketplace_user;
GRANT ALL PRIVILEGES ON marketplace.electronics TO marketplace_user;
