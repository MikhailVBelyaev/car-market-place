# System Health Report

*Generated: 2026-06-21*
*Environment: Local dev copy — production DB restored (121,756 cars)*

---

## Summary

| Component | Status | Notes |
|---|---|---|
| PostgreSQL | ✅ Working | 121,756 cars, clean data |
| Django API (GET endpoints) | ✅ Working | All 6 endpoints respond correctly |
| Django API (POST /api/cars/) | ⚠️ Broken | `created_at` required but not auto-set |
| Django Admin | ✅ Working | Login redirect (302) as expected |
| Frontend (Nginx + React) | ✅ Working | Serves SPA, assets load |
| Nginx → Django proxy | ✅ Working | `/api/*` correctly routed |
| Nginx → ML API proxy | ❌ Broken | Returns 500 (ML API fault) |
| ML API `/healthz` | ✅ Working | `{"status":"ok"}` |
| ML API `/predict` (v1) | ❌ Broken | 500 — scikit-learn version mismatch |
| ML API `/predict2` (v2) | ❌ Broken | 500 — scikit-learn version mismatch |
| ML API validation | ✅ Working | Missing field errors returned correctly |
| Scraper | ⚠️ Not running | Not included in local dev stack |
| Telegram Bot | ⚠️ Not running | Not included in local dev stack |
| Airflow | ⚠️ Not running | Not running on production either |
| Monitoring (Grafana/Prometheus) | ⚠️ Not running | Not included in local dev stack |

---

## 1. PostgreSQL — WORKING

**Status:** Healthy. All data restored from production backup.

```
Total cars:     121,756
Price range:    1,600 – 159,021 BHD
Average price:  12,595 BHD
Date range:     May 2025 → June 4, 2026
Duplicate ads:  0  (car_ad_id is unique)
```

**Data quality issues (NULLs):**

| Field | NULL count | % of total | Impact |
|---|---|---|---|
| `fuel_type` | 60,317 | **49.5%** | High — half the catalogue has no fuel type |
| `color` | 18,444 | 15.2% | Medium — filters/search affected |
| `gear_type` | 3,100 | 2.5% | Low |
| `body_type` | 2,655 | 2.2% | Low — also used in ML predictions |

The fuel_type NULL rate is significant — nearly half the listings were scraped before that field was added (Flyway V4 added the `fuel_type` enum column). Old listings never got backfilled.

**Flyway migration history:** The `flyway_schema_history` table does not exist in the production DB dump. This means Flyway was never the primary migration tool on the production server — the schema was set up via `db/init_db.sql` and `db/init_user.sql`, and migrations were applied manually or not at all. This is a risk: schema and Flyway are out of sync.

---

## 2. Django API — WORKING (with one broken endpoint)

**Base URL:** `http://localhost:8000`

### Working endpoints

| Method | Endpoint | Result |
|---|---|---|
| GET | `/api/cars/` | Returns all 121,756 cars with all 27 fields |
| GET | `/api/cars/{id}/` | Returns single car detail |
| GET | `/api/cars/filtered-list/` | Returns filtered results + available filter options |
| GET | `/api/cars/filters-summary/` | Returns value counts per field (brand, model, fuel_type, …) |
| GET | `/api/cars/dropdown-options/` | Returns 21 brands, 136 models, 8 colors, 4 fuel types, 9 body types |
| GET | `/api/cars/fuel-type-summary/` | Fuel distribution: Gasoline 55,887 / Electric 5,064 / Diesel 358 / Hybrid 130 / NULL 60,317 |

**Filtering works correctly.** Example — Toyota, Gasoline, 2018–2022 returns 1,401 cars.

### Broken endpoint

**`POST /api/cars/`** — returns HTTP 400:
```json
{"created_at": ["This field is required."]}
```
The `created_at` field has a DB default (`CURRENT_TIMESTAMP`) but the Django serializer marks it as required. The scraper presumably sets it explicitly, but the API cannot be used to create a car without passing `created_at` manually. This breaks any client that expects `created_at` to be auto-generated.

### Other observations

- Django `GET /` returns `{"message": "This is an information portal…"}` — this is also the healthcheck URL, polled every 10 seconds, generating log noise.
- Django Admin is accessible at `/admin/` (redirects to login).
- Django is running with `manage.py runserver` — **not safe for production load**. Should be Gunicorn.
- `DEBUG = True` in settings — stack traces exposed on errors.
- `ALLOWED_HOSTS = ['*']` — accepts any Host header.

---

## 3. ML API — BROKEN (both predict endpoints)

**Status:** `GET /healthz` works. All prediction endpoints return HTTP 500.

**Root cause: scikit-learn version mismatch**

The `.pkl` model files were trained with **scikit-learn 1.3.0** but the container is running **scikit-learn 1.5.2**. Between these versions, the internal format of `ColumnTransformer` and `Pipeline` changed, causing:

```
AttributeError: 'str' object has no attribute 'transform'
```

This affects both models:
- `car_price_model.pkl` — used by `/predict` (year + mileage only)
- `car_price_model_v2.pkl` — used by `/predict2` (full features: brand, model, gear_type, color, fuel_type, body_type)

**This bug also affects the production server** — the same images are running there.

**Fix options (two paths):**

*Option A — Pin scikit-learn to 1.3.0 in `ml_api/requirements.txt`:*
```
scikit-learn==1.3.0
```
Rebuild the image. Fast fix, works without retraining.

*Option B — Retrain the model with scikit-learn 1.5.2:*
Run `ml_lab/car_price_model.ipynb`, save new `.pkl` files, rebuild the image. Better long-term.

**Validation works correctly.** If required fields are missing, FastAPI returns proper 422 errors.

---

## 4. Frontend (Nginx + React) — WORKING

**Status:** Serves correctly on `http://localhost:80`.

- React SPA loads (`<title>React App</title>`)
- JS bundle (`main.07f7b73c.js`) and CSS (`main.4ec4ba30.css`) are served at `/static/`
- `/healthz` returns HTTP 200
- `/api/*` proxy to Django — working (HTTP 200)
- `/predict2` proxy to ML API — returns 500 (because ML API is broken, not a proxy config issue)

**Known frontend limitations (from code review):**
- No user authentication UI
- No car detail page — only a listing view
- No pagination on the list (loads all 121,756 records at once — browser performance risk)
- Price Prediction page (`PricePrediction.js`) calls `/predict2` which currently returns 500

---

## 5. Services Not Running Locally

These services are excluded from the local dev compose but are part of the full system:

| Service | Status on Production | Risk |
|---|---|---|
| Scraper | Running (up 2 weeks) | New data is being collected only on production |
| Telegram Bot | Not running (even on production) | Price prediction via Telegram is offline everywhere |
| Airflow | Not running (even on production) | Scheduled scraping DAG is not executing |
| Grafana/Prometheus | Not running (even on production) | No monitoring anywhere |
| Elasticsearch | Not running (even on production) | No log aggregation anywhere |
| Flyway | Not running | DB schema migrations are not tracked |

---

## 6. Performance Observations

| Container | CPU | Memory |
|---|---|---|
| Django | 1.92% | 694 MB |
| ML API | 0.16% | 169 MB |
| PostgreSQL | ~0% (idle) | 105 MB |
| Nginx/Frontend | ~0% | 16 MB |

Django uses **694 MB** for a single-worker `runserver`. With Gunicorn and multiple workers this would multiply. The 121,756-record response from `GET /api/cars/` is sent as one huge JSON array — no pagination — which will cause significant memory and response time spikes under real traffic.

---

## Priority Fix List

| # | Issue | Severity | Effort |
|---|---|---|---|
| 1 | ML API 500 error (sklearn version) | **Critical** | 30 min (pin version + rebuild) |
| 2 | `POST /api/cars/` requires `created_at` | High | 1 hour (make field optional in serializer) |
| 3 | `GET /api/cars/` returns all 121K records at once | High | 2 hours (add DRF pagination) |
| 4 | `manage.py runserver` in production | High | 5 min (switch to Gunicorn) |
| 5 | Telegram Bot not running on production | Medium | investigate tg_bot/.env or image |
| 6 | Airflow not running on production | Medium | deploy airflow service |
| 7 | 49.5% NULL fuel_type in data | Medium | backfill from description or re-scrape |
| 8 | `DEBUG = True` + `ALLOWED_HOSTS = ['*']` | Medium | set via environment variable |
| 9 | Flyway not tracking production schema | Low | run Flyway baseline on production |
