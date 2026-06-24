# Production Server vs GitHub — Comparison

*Generated: 2026-06-21*
*Production server: `100.69.53.111` (Tailscale / oldgamepc)*

---

## TL;DR

The production server runs **pre-built Docker images** — it does not have the full source code. Only config files and the scraper source (mounted as a volume) exist on the filesystem. The rest of the app lives inside the Docker images that were built and loaded at some past point.

---

## Files on Production NOT in GitHub

These exist on the server but are absent from the git repository.

| File | Why it's there | Risk |
|---|---|---|
| `backend/car_marketplace/.env` | Django secrets — correct to exclude from git | Safe, but must be backed up manually |
| `db/.env` | Postgres credentials — correct to exclude | Safe, but must be backed up manually |
| `tg_bot/.env` | Telegram bot token — correct to exclude | Safe, but must be backed up manually |
| `ngrok/.env` | ngrok auth token — correct to exclude | Safe, but must be backed up manually |
| `scraper/requirements.txt` | **Should be in git — it's not a secret** | Risk: if the scraper image needs to be rebuilt, we don't know which versions were used |
| `backup.dump` | Old pg_dump in the project root | Fine, but move to `~/backups/` to keep project dir clean |

### Action Required: commit `scraper/requirements.txt`

The file content (from the production server):
```
requests==2.32.4
beautifulsoup4==4.13.4
pandas==2.3.0
pytz==2024.2
lxml==5.2.1
```

This is already almost identical to what's in `scraper/Dockerfile` (if dependencies are installed there), but having a pinned `requirements.txt` in git ensures reproducible image builds.

---

## Files in GitHub NOT on Production

The production server is minimal by design — images are pre-built. These files exist in git but are not deployed to the server filesystem:

| Directory / File | Reason absent |
|---|---|
| `backend/` (full source) | Code is baked into the `django` Docker image |
| `frontend/src/`, `frontend/public/` | Code baked into the `frontend` image |
| `ml_api/` | Code baked into the `ml_api` image |
| `tg_bot/bot.py`, `tg_bot/Dockerfile` | Code baked into the `tg_bot` image |
| `airflow/` | Airflow is NOT running on production |
| `db/updates/` (Flyway migrations) | Not present — Flyway is not being run on production |
| `prometheus/`, `grafana_data` | Monitoring stack is NOT running on production |
| `terraform/`, `kubernetes-manifests*.yaml` | IaC, not deployed here |
| `databricks/` | Databricks container runs but data volume is empty |
| `CLAUDE.md`, `docs/`, `scripts/` | Created locally, not yet pushed or deployed |

---

## docker-compose.yml Differences

The production has a **different** `docker-compose.yml` from what is in git. Key differences:

| Aspect | GitHub version | Production version |
|---|---|---|
| django | `build: context: ./backend` | `image: django` (pre-built) |
| postgres | `build: context: ./db` | `image: postgres` (official image) |
| frontend | `build: context: ./frontend` + nginx.conf volume | `image: frontend` (pre-built, no volume) |
| ml_api | `build: context: ./ml_api` | `image: ml_api` (pre-built) |
| tg_bot | `build: context: ./tg_bot` | `image: tg_bot` (pre-built) |
| scraper | build + `backend` volume mount | `image: scraper` + only `./scraper` volume |
| ngrok | not in GitHub version | present, `image: ngrok/ngrok:latest` |

The production `docker-compose.yml` is essentially a "runtime" config using pre-built local images, while the GitHub version is a "build from source" config.

**This is a problem:** if the production server needs to be rebuilt from scratch (disk failure, new server), we cannot do it from GitHub alone — we need the Docker images too (or to use `build_and_push_local.sh` to rebuild them).

---

## Services Running on Production

| Service | Status | Notes |
|---|---|---|
| `car-market-place-django-1` | Up 2 weeks (healthy) | Running `manage.py runserver` — not Gunicorn |
| `car-market-place-postgres-1` | Up 2 weeks | PostgreSQL — no healthcheck configured |
| `car-market-place-frontend-1` | Up 2 weeks | Nginx + React |
| `car-market-place-ml_api-1` | Up 2 weeks | FastAPI price predictor |
| `car-market-place-scraper-1` | Up 2 weeks | OLX scraper loop |
| `tg_bot` | **NOT running** (car-marketplace) | Only videocam-ai tg_bot is running |
| `airflow-*` | **NOT running** | No automated DAGs on production |
| `grafana`, `prometheus` | **NOT running** | Monitoring stack offline |
| `elasticsearch` | **NOT running** | Log stack offline |
| `ngrok` | **NOT running** | No remote tunnel |

The server also runs unrelated services: `videocam-ai` (4 containers), `ielts-ai-bot`, `ollama`, `n8n`.

---

## Disk Usage

```
Total:     94 GB
Used:      64 GB (72%)
Available: 26 GB
```

The server has 26 GB free. With 22 MB per DB dump, there is room for years of backups at daily frequency. The large consumers are Docker images (many unrelated projects: stable-diffusion-webui at 26GB, videocam-ai cams_grabber at 15.6GB, Ollama at 5.67GB).

---

## Backup Status

As of 2026-06-21:

| Item | Status |
|---|---|
| `~/backups/car_marketplace/db_2026-06-21_18-40.dump` | **Created today (22 MB)** |
| `~/backups/car_marketplace/settings_2026-06-21_18-40.tar.gz` | **Created today (579 B, 4 .env files)** |
| Local dev copy (`/home/user/backups/car_marketplace/`) | **Copied to this machine** |
| Old `backup.dump` in project root | Stale — from a previous manual backup |
| Automated cron backup | **NOT configured yet** — see `docs/BACKUP_AND_RECOVERY.md` |

---

## Recommended Next Steps

1. **Add cron backup on the server** — see `docs/BACKUP_AND_RECOVERY.md`
2. **Push `scripts/backup.sh` to GitHub** and deploy it to the server via `git pull`
3. **Commit `scraper/requirements.txt`** — it's not a secret and is needed for reproducible builds
4. **Decide on one docker-compose.yml** — either maintain a separate `docker-compose_prod.yml` for the production image-based config, or document that the production file differs
5. **Switch Django to Gunicorn** — production is still running `manage.py runserver`
6. **Add Flyway to production** — migrations are not being run on production; schema must be manually up to date
