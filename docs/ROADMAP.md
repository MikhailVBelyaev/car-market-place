# Roadmap — Car Marketplace

*Last updated: 2026-06-21*

This is the technical roadmap for improving the platform. Items are ordered by impact-to-effort ratio — fix the dangerous things first, then build new features on a solid foundation.

---

## Phase 0 — Harden What Exists (Immediate)

These are bugs and security issues in the current code that should be fixed before anything else.

### 0.1 Fix Django Production Settings

**File:** `backend/car_marketplace/settings.py`

```python
# Change:
DEBUG = True
ALLOWED_HOSTS = ['*']

# To:
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
```

Add to each `.env` file on server:
```
DEBUG=False
ALLOWED_HOSTS=192.168.100.113,100.69.53.111,yourdomain.com
CORS_ALLOWED_ORIGINS=http://yourdomain.com,https://yourdomain.com
```

### 0.2 Move Flyway Credentials to Env File

**File:** `docker-compose.yml` — flyway service currently has `-password=marketplace_user` hardcoded in the command.

Use an env file instead:
```yaml
flyway:
  image: flyway/flyway:10.20.1
  env_file:
    - ./db/.env
  command: >
    -url=jdbc:postgresql://postgres:5432/postgres
    -user=${POSTGRES_USER}
    -password=${POSTGRES_PASSWORD}
    -locations=filesystem:/flyway/sql migrate
```

### 0.3 Switch Django to Gunicorn in docker-compose.yml

**File:** `docker-compose.yml`

```yaml
django:
  command: gunicorn car_marketplace.wsgi:application --bind 0.0.0.0:8000 --workers 2
```

`runserver` is not thread-safe and leaks Django internals. Gunicorn is already in `requirements.txt`.

### 0.4 Rotate Database Password

Change `marketplace_user` password to a strong random value. Update:
- `db/.env`
- `backend/car_marketplace/.env`
- Rebuild and redeploy postgres + django

### 0.5 Set Up Automated Database Backups

Follow `docs/BACKUP_AND_RECOVERY.md`. At minimum: add the cron job on the production server today.

---

## Phase 1 — Observability (1–2 weeks)

The monitoring stack is running but producing no value. Make it useful.

### 1.1 Wire Django Metrics to Prometheus

Add `django-prometheus` to `backend/requirements.txt`:

```python
# settings.py
INSTALLED_APPS += ['django_prometheus']
MIDDLEWARE = ['django_prometheus.middleware.PrometheusBeforeMiddleware'] + MIDDLEWARE + \
             ['django_prometheus.middleware.PrometheusAfterMiddleware']

# urls.py
urlpatterns += [path('metrics/', include('django_prometheus.urls'))]
```

Update `prometheus/prometheus.yml` to scrape `django:8000/metrics/`.

### 1.2 Add Grafana Dashboards

Import standard dashboards:
- **Node Exporter** (host CPU/memory/disk) — ID 1860
- **Django Prometheus** — ID 9528
- **Postgres Exporter** — ID 9628 (add `postgres_exporter` container)
- **cAdvisor** — ID 14282

### 1.3 Connect Elasticsearch for Logs

Add `filebeat` service to docker-compose.yml to tail container logs and ship to Elasticsearch. Or simpler: add a Django logging handler to write JSON to stdout and let Filebeat pick it up.

```yaml
# docker-compose.yml
filebeat:
  image: docker.elastic.co/beats/filebeat:8.13.4
  volumes:
    - /var/lib/docker/containers:/var/lib/docker/containers:ro
    - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
```

### 1.4 Grafana Alerting

Set up alerts for:
- Django returning 5xx > 5% over 5 minutes
- Postgres connections > 80
- Disk usage > 80%
- Any service container restarting repeatedly

---

## Phase 2 — Data Pipeline Improvements (2–4 weeks)

### 2.1 Parameterize the Airflow DAG

Current `scrape_predict_dag.py` calls a hardcoded script for one brand/model (lacetti white). Refactor to iterate over `scraper/brands_models.json`:

```python
# airflow/dags/scrape_predict_dag.py
import json

with open('/app/scraper/brands_models.json') as f:
    brands_models = json.load(f)

for entry in brands_models:
    BashOperator(
        task_id=f"scrape_{entry['brand']}_{entry['model']}",
        bash_command=f"cd /app/backend && python run_task.py --brand {entry['brand']} --model {entry['model']}"
    )
```

### 2.2 Stop the Scraper's Sleep Loop

The `scraper` service runs a `while True: scrape(); sleep(3600)` loop and also has `restart: always`. This is fragile and hard to observe. Move scraping fully into Airflow:

- Remove `restart: always` from `scraper`
- Drive scraping exclusively via the Airflow DAG
- Run the scraper container as a short-lived task (Airflow `DockerOperator` or `BashOperator`)

### 2.3 Automated ML Model Retraining

Add an Airflow DAG that runs weekly:

1. Export latest data to Parquet (`extract_data/export_pg_to_parquet.py`)
2. Train model (`ml_lab/car_price_model.ipynb` converted to a script)
3. Save new `.pkl` to `ml_api/models/`
4. Restart ML API container to pick up new model

### 2.4 Add Deduplication to Scraper

The `cars` table uses `car_ad_id` as a unique identifier per listing. Make the scraper do an upsert (INSERT … ON CONFLICT DO UPDATE) rather than failing or creating duplicates when re-scraping the same listing.

---

## Phase 3 — API & Feature Completeness (4–8 weeks)

### 3.1 User Authentication

The `users` table exists (created in V2 migration). Wire it up:

- Django `User` model or custom model extending `AbstractBaseUser`
- JWT authentication via `djangorestframework-simplejwt`
- Endpoints: `POST /api/auth/register/`, `POST /api/auth/login/`, `POST /api/auth/refresh/`
- Frontend: Login/Register page, store JWT in localStorage, attach to API calls

### 3.2 Favorites

Table already exists (`marketplace.favorites`). Add:
- `Favorite` Django model (FK to User + FK to Car)
- API: `POST /api/cars/{id}/favorite/`, `DELETE /api/cars/{id}/favorite/`, `GET /api/favorites/`
- Frontend: heart icon on car cards, saved favorites page

### 3.3 Reviews / Ratings

Table exists (`marketplace.reviews`). Add:
- Review model with rating (1–5) + text
- API: `POST /api/cars/{id}/reviews/`, `GET /api/cars/{id}/reviews/`
- Frontend: star rating UI + comment list on car detail page

### 3.4 Car Detail Page (Frontend)

Currently only a list view exists. Add a dedicated `/cars/:id` route that shows:
- Full description and details
- Photo gallery (if photos added to schema)
- Price prediction for this listing's attributes (call `/predict2`)
- Reviews
- Seller contact info

### 3.5 Pagination on the API

`GET /api/cars/` returns all records. Add DRF `PageNumberPagination`:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

### 3.6 Add HTTPS

- Use Certbot + Let's Encrypt on the production server, or
- Terminate TLS at Cloudflare / a simple reverse proxy in front of Nginx

---

## Phase 4 — Reliability & Scale (ongoing)

### 4.1 Docker Resource Limits

Prevent one runaway container from starving others:

```yaml
# docker-compose.yml — add to each service
deploy:
  resources:
    limits:
      memory: 512m
      cpus: '0.5'
```

### 4.2 Separate Airflow Postgres

Move Airflow's metadata DB off the main Postgres to avoid resource contention:

```yaml
# docker-compose.yml
airflow-postgres:
  image: postgres:15
  environment:
    POSTGRES_DB: airflow
    POSTGRES_USER: airflow
    POSTGRES_PASSWORD: airflow
```

Update `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` to point to `airflow-postgres:5432/airflow`.

### 4.3 Health Checks on All Services

Current: only django has a healthcheck. Add to critical services:

```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U marketplace_user"]
    interval: 10s
    timeout: 5s
    retries: 5

ml_api:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8500/healthz"]
    interval: 30s
    timeout: 5s
    retries: 3
```

### 4.4 Database Connection Pooling

Django opens one connection per worker. Under load this saturates Postgres. Add PgBouncer:

```yaml
pgbouncer:
  image: edoburu/pgbouncer
  environment:
    DB_USER: marketplace_user
    DB_PASSWORD: ${POSTGRES_PASSWORD}
    DB_HOST: postgres
    DB_NAME: postgres
    POOL_MODE: transaction
  ports:
    - "5432:5432"
```

Update Django `DB_HOST` to point to `pgbouncer`.

### 4.5 Clean Up Duplicate Files

- `dump_cars.json` exists in both `/db/` and `/backend/` — consolidate to one location, reference by path
- Remove committed `.dump` file from git (it's 22MB binary, slows clones)

---

## Phase 5 — Future Enhancements

These require significant new development and should be done after Phase 0–3 are complete.

| Feature | Notes |
|---|---|
| Photo uploads | Add `photos` table and S3/local storage; scraper should save images |
| Real-time messaging | Django Channels (WebSocket) between buyers and sellers |
| Mobile app | React Native sharing API with the web app |
| Car recommendation engine | Collaborative filtering or content-based on `marketplace.cars` |
| Price trend charts | Store historical prices by `car_ad_id`, chart over time |
| Multi-region expansion | Parameterize scraper for Kuwait, UAE OLX sites |
| ML model explainability | Add SHAP values to `/predict2` response so users understand the estimate |
| Kubernetes production deploy | Finish and document AKS/GCP manifests; add Helm charts |

---

## Priority Summary

| Priority | Item | Effort |
|---|---|---|
| NOW | Fix DEBUG/ALLOWED_HOSTS | 30 min |
| NOW | Automated DB backup (cron) | 1 hour |
| NOW | Gunicorn instead of runserver | 5 min |
| NOW | Rotate DB password | 30 min |
| HIGH | Django Prometheus + Grafana dashboards | 1 day |
| HIGH | Parameterize Airflow DAG | half day |
| HIGH | User auth + JWT | 3 days |
| MEDIUM | Favorites + Reviews API | 2 days |
| MEDIUM | Car detail page (frontend) | 2 days |
| MEDIUM | API pagination | 2 hours |
| MEDIUM | HTTPS / TLS | half day |
| LOW | Resource limits in Compose | 1 hour |
| LOW | Separate Airflow Postgres | 1 hour |
| LOW | ML model retraining DAG | 2 days |
| LOW | PgBouncer connection pooling | half day |
