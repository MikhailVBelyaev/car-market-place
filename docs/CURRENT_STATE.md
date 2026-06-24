# Current State — Car Marketplace

*Snapshot: 2026-06-21*

---

## What Is Built and Working

### Core Platform
- **React frontend** served by Nginx, proxying `/api/*` to Django and `/predict2` to the ML API
- **Django REST API** (5 endpoints: list, detail, filtered list, filters summary, dropdown options)
- **PostgreSQL 15** with `marketplace` schema, ~25-column `cars` table populated from OLX scraper data
- **Flyway migrations** (V1–V8) managing schema changes via SQL files in `db/updates/`
- **FastAPI ML API** serving price predictions (v1 and v2 models, joblib/pickle format)
- **OLX Scraper** running in a Docker container, scraping car listings and posting to Django API
- **Telegram Bot** accepting user input and calling ML API for price predictions
- **Docker Compose** orchestrating all services on a single-node local server

### Data Pipeline
- Scraper polls OLX → posts to `POST /api/cars/` → stored in PostgreSQL
- Airflow `scrape_predict_dag` runs daily (currently calls `run_task_lacetti_white.py` — single brand/model)
- `extract_data/export_pg_to_parquet.py` exports data to Parquet for ML training
- Databricks notebooks support offline model training

### Infrastructure & Ops
- `build_and_push_local.sh` — deploys any service to the production server via rsync + SSH
- `fetch_remote_dump.sh` — pulls a pg_dump from the production server to local
- GitHub Actions workflow triggers Flyway migration on push to `db/updates/**`
- Monitoring stack: Prometheus + Grafana + cAdvisor running (but dashboards not configured)
- Elasticsearch running but not yet wired to any log shipper
- Terraform configs exist for Azure AKS and GCP (not actively used)
- Kubernetes manifests exist for AKS and GCP (not actively deployed)
- ngrok tunnel available for temporary remote access

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│  Production Server (100.69.53.111 or 192.168.100.113)   │
│  Docker Compose — network: car-market-net                │
│                                                          │
│  ┌─────────┐   /api/*    ┌──────────┐                   │
│  │ Nginx   │────────────►│  Django  │                   │
│  │ :80     │   /predict2 │  :8000   │                   │
│  │(React)  │──────────┐  └────┬─────┘                   │
│  └─────────┘          │       │ ORM                     │
│       ▲               │  ┌────▼──────┐  ┌────────────┐  │
│   Browser             │  │ Postgres  │◄─│  Flyway    │  │
│                       │  │ :5432     │  │ migrations │  │
│                       │  └────▲──────┘  └────────────┘  │
│                       │       │                          │
│                       │  ┌────┴──────┐                   │
│                       │  │ Airflow   │ (daily DAG)       │
│                       │  │ :8081     │                   │
│                       │  └────┬──────┘                   │
│                       │       │ BashOperator             │
│                       │  ┌────▼──────┐                   │
│                       │  │ Scraper   │──► OLX (external) │
│                       │  └───────────┘                   │
│                       │                                  │
│                       │  ┌────────────┐                  │
│                       └─►│  ML API   │                  │
│                          │  :8500    │                   │
│                          └─────▲─────┘                   │
│                                │                         │
│                          ┌─────┴──────┐                  │
│                          │ Telegram   │◄── Users         │
│                          │ Bot        │                   │
│                          └────────────┘                  │
│                                                          │
│  Monitoring: Prometheus:9090, Grafana:3000, cAdvisor:8080│
│  Logs:       Elasticsearch:9200 (not connected yet)      │
│  Tunnel:     ngrok:4040                                  │
└──────────────────────────────────────────────────────────┘
```

---

## What Is Partially Done

| Feature | Status | Gap |
|---|---|---|
| User authentication | Schema exists (`users` table in V2) | Not wired to Django; no login/register flow |
| Favorites | Table created (V3) | Not exposed in Django API or UI |
| Reviews | Table created (V2) | Not exposed anywhere |
| Airflow pipeline | DAG exists | Only scrapes one brand/model (lacetti white); not parameterized |
| Monitoring (Grafana) | Container running | No dashboards configured |
| Elasticsearch | Container running | No log shipper (Filebeat/Logstash) connected |
| Secure messaging | Mentioned in roadmap | Not started |
| Kubernetes deployment | Manifests exist | Not actively maintained or deployed |
| Terraform (Azure/GCP) | Configs exist | Not actively used |
| Databricks | Notebooks + container | Mounted as volume but `tail -f /dev/null` — no active integration |
| ML model retraining | Notebook exists | No automated retraining pipeline |

---

## Known Issues & Security Concerns

### Critical (fix before any real production traffic)

1. **`DEBUG = True` in `settings.py`**
   - Django exposes full stack traces in HTTP responses when DEBUG is on
   - Fix: `DEBUG = os.getenv('DEBUG', 'False') == 'True'`

2. **`ALLOWED_HOSTS = ['*']`**
   - Allows HTTP Host header injection attacks
   - Fix: set to actual domain/IP list via environment variable

3. **Hardcoded DB credentials in `docker-compose.yml`**
   - Flyway command has `-password=marketplace_user` in plain text
   - Fix: use `flyway.password` via env file or Docker secret

4. **Default credentials `marketplace_user:marketplace_user`**
   - Same username and password is trivially guessable
   - Fix: rotate to a strong random password, stored in `.env` only

5. **No DB backup automation**
   - Single manual script, no schedule, no off-server copy
   - Fix: see `docs/BACKUP_AND_RECOVERY.md`

### Moderate

6. **Django `runserver` in production docker-compose**
   - `docker-compose.yml` line 5: `python manage.py runserver` — not production-safe
   - Should use Gunicorn: `gunicorn car_marketplace.wsgi:application --bind 0.0.0.0:8000`

7. **Airflow and app share the same Postgres instance**
   - Airflow metadata tables live in `public` schema of the same `postgres` DB
   - Heavy Airflow work (scheduling, retries, DAG parsing) competes with app queries
   - Fix: separate Airflow to its own small Postgres, or use SQLite for SequentialExecutor

8. **`Car` model is `managed = False`**
   - Django migrations won't modify the actual table — Flyway owns it
   - Risk: if someone runs `python manage.py migrate` expecting a schema change, nothing happens and there's no warning
   - Acceptable pattern but must be documented (now in CLAUDE.md)

9. **No HTTPS / TLS**
   - Nginx serves on port 80 with no TLS termination
   - Fix: add Certbot + Let's Encrypt, or terminate TLS at a load balancer

10. **`CORS_ALLOWED_ORIGINS` only includes `localhost:3000`**
    - Will block requests from the actual production domain
    - Fix: add production domain to the list or read from environment

### Minor

11. `scraper` runs on a hardcoded 3600s sleep loop inside the container — not driven by Airflow scheduler, duplicating work
12. `dump_cars.json` (~22MB) is duplicated in both `/db/` and `/backend/`
13. Elasticsearch is started but nothing writes to it (no Filebeat, no Django logging handler)
14. `databricks` service is `python:3.12-slim` running `tail -f /dev/null` — pure placeholder
15. No resource limits on any Docker service — a runaway scraper can starve the DB

---

## Tech Stack Summary

| Layer | Technology | Version |
|---|---|---|
| Frontend | React | 19.0.0 |
| HTTP routing | Nginx (Alpine) | latest |
| Backend API | Django + DRF | 5.1.4 |
| ML inference | FastAPI + joblib | latest |
| Database | PostgreSQL | 15 |
| Migrations | Flyway | 10.20.1 |
| Scraping | BeautifulSoup + Selenium | 4.13.4 |
| Bot | python-telegram-bot | latest |
| Orchestration | Apache Airflow | 2.9.1 |
| Containerization | Docker Compose | v2 |
| Monitoring | Prometheus + Grafana | latest |
| IaC | Terraform | — |
| CI/CD | GitHub Actions | — |
| Runtime | Python | 3.12 |

---

## Data Model (Core Table)

`marketplace.cars` — the only table actively used by the application today:

```
car_id          (PK, bigint)
brand           (varchar)
model           (varchar)
year            (int)
price           (numeric)
mileage         (int)
gear_type       (enum: AT, MT, CVT, AMT, DSG)
fuel_type       (enum: petrol, diesel, electric, hybrid, gas)
body_type       (varchar)
color           (varchar)
condition       (enum: new, used)
vehicle_type    (enum: sedan, suv, hatchback, …)
location        (varchar)
description     (text)
description_detail (text)
reference_url   (varchar)
car_ad_id       (varchar, unique)
owner_name      (varchar)
owner_phone     (varchar)
owner_count     (int)
customer_paid_tax (boolean)
additional_options (text)
created_at      (timestamp)
```

Schema-only tables (created but unused): `reviews`, `categories`, `favorites`, `users`, `transactions`.

---

## Deployment Flow (Current)

```
Developer machine
  │
  ├─ git push → GitHub
  │     └─ GitHub Action → SSH → git pull → flyway migrate (only for db/updates/** changes)
  │
  └─ ./build_and_push_local.sh [service]
        └─ rsync source → 192.168.100.113
        └─ docker build on remote
        └─ docker compose up -d [service]
```

Production data pull:
```
./fetch_remote_dump.sh
  └─ SSH → pg_dump inside container → docker cp → SCP to local
```
