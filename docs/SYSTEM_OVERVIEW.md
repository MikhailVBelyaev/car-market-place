# UzVehicles Market — System Overview

## Architecture

```
OLX.uz ──► Scraper ──► Django API ──► PostgreSQL
                              │
                    ┌─────────┼─────────┐
                    │         │         │
               ML Model   Airflow    Telegram
               (FastAPI)  (DAGs)      Bot
                    │         │         │
               /predict2  tg_channel  @MVehicleBot
                          (Mon/Wed/Fri posts)
                              │
                      @UzVehiclesMarket
                         (channel)
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| django | 8000 | REST API, business logic, price history |
| postgres | 5433 | Main database (14+ months of listings) |
| ml_api | 8500 | FastAPI RandomForest price prediction |
| tg_bot | — | @MVehicleBot prediction + analysis bot |
| car_vision_api | 8600 | Claude vision — car photo analysis |
| tg_channel | — | Analytics channel auto-poster |
| airflow | 8081 | DAG scheduler (scraping + channel posts) |

## Bot Commands

| Command | Description | Requires |
|---------|-------------|---------|
| `/start` | Price prediction flow | — |
| `/compare` | Own car vs Taxi calculator | Prior `/start` |
| `/forecast` | 3-year value depreciation | Prior `/start` |
| `/fotos` | AI photo analysis | Anthropic API key |
| `/check` | Submit photos immediately | Active /fotos session |
| `/cancel` | Exit any flow | — |

## Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cars/smart-price/` | GET | Current market price (real listings, progressive mileage band) |
| `/api/cars/price-history/` | GET | Monthly price trend with hedonic regression |
| `/api/cars/brand-models/` | GET | All brands and their models |
| `/api/cars/brand-ranking/` | GET | Top brands by listing count (channel use) |
| `/api/cars/price-movers/` | GET | Models with biggest price change (channel use) |
| `/api/cars/weekly-digest/` | GET | Full weekly market summary (channel use) |
| `/predict2` | POST | ML price prediction (ml_api) |
| `/analyze` | POST | Car photo analysis (car_vision_api) |

## Pricing Logic

### Smart Price (current market)
1. Try last 30 days, ±25% mileage band → need ≥5 listings
2. Try last 60 days, ±25% band
3. Try last 30 days, ±50% band
4. Try last 90 days, ±50% band
5. Fall back to ML prediction

### Price History (trend chart)
Uses **hedonic regression** per month:
- Takes all listings for the spec (no mileage filter)
- Computes one pooled `price/km` slope across all data
- Per month: `price_at_your_km = avg_price + slope × (your_km − avg_km)`
- Shows what YOUR car specifically would have cost each month

### Own Car vs Taxi (/compare)
```
monthly_car = (car_price × annual_depr_rate / 12) + (km×30 × fuel_l100/100 × $0.65) + $30
monthly_taxi = km × 30 × taxi_price_per_km
```
Depreciation rates from real market data (Chevrolet -9%, BYD -31%, etc.)

### Value Forecast (/forecast)
- Derives monthly depreciation rate from hedonic price history (real data)
- Falls back to brand-level estimates if insufficient history
- Projects 36 months forward: `value(m) = current_price × (1 + monthly_rate)^m`

## Channel Schedule (Airflow)

| DAG | Schedule | Post type |
|-----|----------|-----------|
| tg_channel_monday | Mon 09:00 | Brand ranking chart |
| tg_channel_wednesday | Wed 09:00 | Price movers chart |
| tg_channel_friday | Fri 09:00 | Full weekly digest |

## Environment Files

| File | Key variables |
|------|--------------|
| `backend/car_marketplace/.env` | `SECRET_KEY`, `DB_*` |
| `db/.env` | `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| `tg_bot/.env` | `BOT_TOKEN`, `ML_API_URL`, `DJANGO_URL`, `CAR_VISION_URL` |
| `tg_channel/.env` | `CHANNEL_BOT_TOKEN`, `CHANNEL_ID`, `DJANGO_URL` |
| `car_vision_api/.env` | `ANTHROPIC_API_KEY`, `VISION_MODEL` |

## Deploy

```bash
# Local dev stack
docker compose -f docker-compose.devlocal.yml -p car-dev up --build

# Post to channel manually
docker compose -f docker-compose.devlocal.yml -p car-dev --profile channel run --rm tg_channel friday

# Production deploy
./build_and_push_local.sh django
./build_and_push_local.sh frontend
```
