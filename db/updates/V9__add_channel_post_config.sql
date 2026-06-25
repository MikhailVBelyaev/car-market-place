CREATE TABLE IF NOT EXISTS marketplace.channel_post_config (
    post_type    VARCHAR(50)  PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    description  TEXT,
    enabled      BOOLEAN      DEFAULT FALSE,
    schedule     VARCHAR(50),
    last_posted  TIMESTAMPTZ
);

INSERT INTO marketplace.channel_post_config
    (post_type, name, description, enabled, schedule) VALUES
('brand_ranking',       'Brand Ranking',         'Top brands by weekly listing volume with week-over-week change',        TRUE,  'Mon 09:00'),
('price_movers',        'Price Movers',          'Biggest price risers and fallers this week across all models',          TRUE,  'Wed 09:00'),
('weekly_digest',       'Weekly Digest',         'Full weekly market summary: brands, models, prices, depreciation',      TRUE,  'Fri 09:00'),
('color_premium',       'Color Premium',         'Which car colors hold value best — price comparison by color',         FALSE, 'Monthly'),
('gear_premium',        'Gear Premium',          'Automatic vs Manual transmission price difference by brand',            FALSE, 'Monthly'),
('age_depreciation',    'Age Depreciation',      'Year-by-year value loss for top 3 brands (2015–2024)',                 FALSE, 'Monthly'),
('best_value',          'Best Value Deals',      'Listings priced below 25th percentile for their model and year',       FALSE, 'Weekly'),
('seasonal_trends',     'Seasonal Trends',       '14-month price chart — best and worst months to buy',                  FALSE, 'Monthly'),
('market_breadth',      'Market Breadth',        'How many cars in each budget: under $5k / $10k / $20k / $30k+',       FALSE, 'Monthly'),
('mileage_depreciation','Mileage Depreciation',  'Real cost per km: which models lose most value per 10,000 km driven', FALSE, 'Monthly')
ON CONFLICT (post_type) DO NOTHING;
