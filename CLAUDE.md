# CLAUDE.md — UzVehicles Car Marketplace

Project guide for AI assistants and new contributors.

## What This Project Is

A full-stack car market intelligence platform for Uzbekistan. It scrapes listings from OLX.uz, stores them in PostgreSQL (14+ months of data), serves a Django REST API, and delivers insights through three channels:

- **@MVehicleBot** — Telegram bot for real-time price prediction, photo analysis, own-car-vs-taxi calculator, and 3-year value forecasts
- **@UzVehiclesMarket** — Automated analytics channel (Mon/Wed/Fri posts in Uzbek + Russian)
- **Web frontend** — React SPA for browsing listings

Production deployments available for Azure AKS, GCP, and Oracle Cloud.

---

## Quick Commands

### Local dev stack (devlocal)
```bash
docker compose -f docker-compose.devlocal.yml -p car-dev up --build
```

### Post to Telegram analytics channel manually
```bash
# Friday digest
docker compose -f docker-compose.devlocal.yml -p car-dev --profile channel run --rm tg_channel friday
# Monday brand ranking
docker compose -f docker-compose.devlocal.yml -p car-dev --profile channel run --rm tg_channel monday
# Wednesday price movers
docker compose -f docker-compose.devlocal.yml -p car-dev --profile channel run --rm tg_channel wednesday
```

### Dry-run (generate chart without posting)
```bash
docker compose -f docker-compose.devlocal.yml -p car-dev --profile channel run --rm tg_channel friday --dry-run
```

### Deploy to production server
```bash
./build_and_push_local.sh django
./build_and_push_local.sh frontend
./build_and_push_local.sh ml_api
./build_and_push_local.sh   # all services
```

### Pull a fresh DB dump from production
```bash
./fetch_remote_dump.sh
# saves to ./backup_remote_YYYY-MM-DD_HH-MM.dump
```

### Django management
```bash
docker compose -f docker-compose.devlocal.yml -p car-dev exec django python manage.py migrate
docker compose -f docker-compose.devlocal.yml -p car-dev exec django python manage.py shell
```

### Connect to Postgres
```bash
docker compose -f docker-compose.devlocal.yml -p car-dev exec postgres psql -U marketplace_user postgres
# Schema: marketplace
```

---

## Architecture at a Glance

```
OLX.uz ──► Scraper ──► Django API ──► PostgreSQL (14+ months)
                              │
                    ┌─────────┼──────────────┐
                    │         │              │
               ML API     Airflow DAGs    Telegram
              (FastAPI)  Mon/Wed/Fri      Bot (@MVehicleBot)
                    │         │              │
               /predict2  tg_channel     /start /compare
                       (@UzVehiclesMarket)  /forecast /fotos

Browser → Nginx (port 80) ──► React SPA
                          └──► /api/*     → Django (8000)
                          └──► /predict2  → ML API (8500)
```

### Services (docker-compose.devlocal.yml, project: car-dev)

| Service | Port | Purpose |
|---|---|---|
| frontend | 80 | React via Nginx |
| django | 8000 | Django REST API |
| postgres | 5433 | PostgreSQL 15, schema `marketplace` |
| flyway | — | SQL migrations on startup |
| ml_api | 8500 | FastAPI RandomForest price predictor |
| car_vision_api | 8600 | FastAPI + Claude vision (photo analysis) |
| tg_bot | — | @MVehicleBot Telegram bot |
| tg_channel | — | Analytics channel poster (profile: channel) |
| scraper | — | OLX scraper |
| airflow-webserver | 8081 | Airflow UI |
| airflow-scheduler | — | DAG runner |
| ngrok | 4040 | Tunnel for remote access |

---

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Price prediction: brand → model → year → mileage → gear → color → market price + chart |
| `/compare` | Own car vs Taxi calculator: daily km + taxi price → monthly cost breakdown + 3-year chart |
| `/forecast` | 3-year value depreciation projection (uses real market data via hedonic regression) |
| `/fotos` | Send car photos → AI analysis (condition, brand/model, damage areas) |
| `/check` | Submit photos immediately for analysis |
| `/cancel` | Exit any active flow |

After `/start` completes, the keyboard shows `/compare` and `/forecast` buttons automatically.

---

## Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/cars/smart-price/` | GET | Current market price — progressive mileage band search, real listings |
| `/api/cars/price-history/` | GET | Monthly price trend with hedonic regression (`?mileage=N` for your-car value) |
| `/api/cars/brand-models/` | GET | All brands and their models (for bot keyboard) |
| `/api/cars/brand-ranking/` | GET | Top brands by listing count, week-over-week change |
| `/api/cars/price-movers/` | GET | Models with biggest price change vs previous period |
| `/api/cars/weekly-digest/` | GET | Full weekly market summary for channel digest |
| `/predict2` | POST | ML price prediction (ml_api, port 8500) |
| `/analyze` | POST | Car photo analysis via Claude (car_vision_api, port 8600) |

### Smart Price Logic
1. Last 30d, ±25% mileage → need ≥5 listings
2. Last 60d, ±25% mileage
3. Last 30d, ±50% mileage
4. Last 90d, ±50% mileage
5. Falls back to ML `/predict2`

### Hedonic Regression (Price History)
When `?mileage=N` is supplied: computes one pooled `USD/km` slope across all months, then per month: `price_at_your_km = avg_price + slope × (your_km − avg_km)`. Shows what YOUR specific car would have cost each month, not the population average.

---

## Key File Locations

| What | Where |
|---|---|
| Django settings | `backend/car_marketplace/settings.py` |
| Django env vars | `backend/car_marketplace/.env` (not in git) |
| Database env | `db/.env` (not in git) |
| Telegram bot | `tg_bot/bot.py` |
| Telegram bot env | `tg_bot/.env` (not in git) |
| Channel poster | `tg_channel/post.py` |
| Channel env | `tg_channel/.env` (not in git) |
| Car Vision API | `car_vision_api/main.py` |
| Car Vision env | `car_vision_api/.env` (not in git) |
| Flyway migrations | `db/updates/V*.sql` |
| Car ORM model | `backend/cars/models.py` |
| API views | `backend/cars/views.py` |
| API routes | `backend/cars/urls.py` |
| ML API | `ml_api/main.py` |
| ML models (binary) | `ml_api/models/*.pkl` (not in git — too large) |
| Airflow DAGs | `airflow/dags/` |
| Channel DAG | `airflow/dags/tg_channel_dag.py` |
| Scraper logic | `scraper/` |
| Nginx config | `frontend/nginx.conf` |
| Documentation | `docs/` |
| Mobile app (Mini App) | `mobile_app/` |
| Deploy scripts | `build_and_push_local.sh`, `build_and_push_ACR.sh` |

---

## Environment Variables

### Backend (`backend/car_marketplace/.env`)
```
SECRET_KEY=<django-secret>
DB_NAME=postgres
DB_USER=marketplace_user
DB_PASSWORD=<password>
DB_HOST=postgres
DB_PORT=5432
```

### Database (`db/.env`)
```
POSTGRES_USER=marketplace_user
POSTGRES_PASSWORD=<password>
```

### Telegram Bot (`tg_bot/.env`)
```
BOT_TOKEN=<telegram-bot-token>
ML_API_URL=http://ml_api:8500
DJANGO_URL=http://django:8000
CAR_VISION_URL=http://car-vision-api:8600
PHOTOS_IDLE_TIMEOUT=30
CHECK_AUTO_TIMEOUT=15
```

### Analytics Channel (`tg_channel/.env`)
```
CHANNEL_BOT_TOKEN=<same-or-different-bot-token>
CHANNEL_ID=@UzVehiclesMarket
DJANGO_URL=http://django:8000
```

### Car Vision API (`car_vision_api/.env`)
```
ANTHROPIC_API_KEY=<anthropic-key>
VISION_MODEL=claude-haiku-4-5-20251001
```

---

## Database Schema

- **Instance:** PostgreSQL 15
- **Database:** `postgres` / **Schema:** `marketplace`
- **Main table:** `marketplace.cars` — brand, model, year, price, mileage, gear_type, fuel_type, body_type, color, condition, location, owner_*, created_at, …
- **Django model:** `managed = False` — Django reads; Flyway owns schema
- **Migrations:** `db/updates/V1__*.sql` through `V8__*.sql`

---

## Analytics Channel Schedule (Airflow)

| DAG | Cron | Post |
|-----|------|------|
| `tg_channel_monday` | `0 9 * * 1` | Brand ranking chart |
| `tg_channel_wednesday` | `0 9 * * 3` | Price movers (risers/fallers) |
| `tg_channel_friday` | `0 9 * * 5` | Full weekly digest |

---

## Mobile App

See `mobile_app/README.md`. Decision: **Telegram Mini App** (not native Android/iOS).
- 90%+ Telegram penetration in Uzbekistan
- Zero installation friction
- Shared auth via Telegram `initData`
- Working prototype: `mobile_app/index.html`

---

## Documentation

| File | Contents |
|------|----------|
| `docs/PRESENTATION.md` | Investor/partner pitch — problem, solution, market, business model |
| `docs/SYSTEM_OVERVIEW.md` | Technical reference — all endpoints, services, deploy commands |
| `mobile_app/README.md` | Mobile strategy — why Telegram Mini App, feature spec, timeline |

---

## Deployment Targets

| Target | How |
|---|---|
| Local dev | `docker compose -f docker-compose.devlocal.yml -p car-dev up --build` |
| Local server (192.168.100.113) | `./build_and_push_local.sh` via SSH + Docker Compose |
| Production remote (100.69.53.111) | SSH + Docker Compose |
| Azure AKS | Terraform → ACR → `kubernetes-manifests.yaml` |
| GCP | `terraform_gcp/` → `kubernetes-manifests_gcp.yaml` |
| Oracle Cloud | Podman — `oracle/` scripts |

---

## Known Issues

1. **`DEBUG = True`** in `settings.py` — never flip without setting `ALLOWED_HOSTS` and `SECRET_KEY` from env.
2. **`ALLOWED_HOSTS = ['*']`** — insecure; set to domain/IP list in production.
3. **Hardcoded DB credentials** in `docker-compose.yml` flyway command — should move to env file.
4. **`Car` model is `managed = False`** — Django migrations do NOT touch the real table; always use Flyway for schema changes.
5. **ML model files not in git** — `*.pkl` files are 200MB+; store in object storage and mount at deploy time.
6. **`ANTHROPIC_API_KEY` must be filled** in `car_vision_api/.env` for photo analysis to work.
7. **Airflow shares Postgres** with the app — heavy DAG workloads can affect app DB performance.
