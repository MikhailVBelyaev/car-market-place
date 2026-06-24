# Backup & Recovery — Production Server

## Current State (as of 2026-06-21)

There is **one manual backup mechanism** in the repo:

```bash
./fetch_remote_dump.sh
```

It SSH-es into `100.69.53.111`, runs `pg_dump` inside the postgres container, copies the dump file out of the container with `docker cp`, then SCPs it to your local machine. The file lands as:

```
./backup_remote_YYYY-MM-DD_HH-MM.dump   # pg_dump custom format (-F c)
```

A dated dump file `backup_remote_2026-01-29_22-47.dump` is already committed to the repo, which is the only persistent backup today.

**Problems with the current approach:**
- Manual — someone has to remember to run it
- No rotation — old dumps are never cleaned up
- Dump stored inside the Postgres Docker volume path (`/var/lib/postgresql/data/backup.dump`) — survives only as long as the volume exists
- No off-server copy unless you run the script locally
- No backup for application settings / `.env` files

---

## Recommended Backup Strategy

### 1. Automated Daily DB Dump on the Server

Add a cron job directly on the production host (`100.69.53.111`). SSH in once and install it:

```bash
ssh user@100.69.53.111
crontab -e
```

Add:
```cron
# Daily at 02:00 — dump Postgres to /home/user/backups/
0 2 * * * docker compose -f /home/user/Projects/car-market-place/docker-compose.yml \
  exec -T postgres pg_dump -U marketplace_user -F c -b postgres \
  > /home/user/backups/car_marketplace_$(date +\%F).dump

# Keep only last 14 days
0 3 * * * find /home/user/backups/ -name "car_marketplace_*.dump" -mtime +14 -delete
```

This produces one dump per day, keeps 14 of them (≈ 2 weeks retention), and requires no code changes.

---

### 2. Copy Dumps Off-Server (3-2-1 Rule)

Running a dump on the server is not enough — if the server dies, the dump dies too. Add a second cron on **your local machine** (or a second server) to pull the latest dump nightly:

```bash
# On your LOCAL machine — runs at 03:30 (after server dump finishes)
30 3 * * * rsync -az --delete \
  user@100.69.53.111:/home/user/backups/ \
  /your-local-path/backups/car_marketplace/
```

Or use `fetch_remote_dump.sh` (already in the repo) as the basis — just wrap it in a cron.

---

### 3. Backup `.env` and Settings Files

Application settings are not in git (intentionally). They live only on the server. Back them up too:

```bash
# On the production server — add to the same cron or run once manually
tar -czf /home/user/backups/settings_$(date +%F).tar.gz \
  /home/user/Projects/car-market-place/backend/car_marketplace/.env \
  /home/user/Projects/car-market-place/db/.env \
  /home/user/Projects/car-market-place/tg_bot/.env \
  /home/user/Projects/car-market-place/ngrok/.env
```

Store this archive in the same `/home/user/backups/` directory so the rsync above picks it up automatically.

**Important:** these files contain secrets. Keep the off-server copy encrypted or in a private location (not a shared drive, not GitHub).

---

### 4. Optional — Airflow DAG for Backup

Since Airflow is already running, you can add a DAG that automates the dump. This is better than a cron because you get visibility (logs, retries, alerts) in the Airflow UI.

Create `airflow/dags/backup_dag.py`:

```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

with DAG(
    dag_id="daily_db_backup",
    start_date=datetime(2026, 6, 22),
    schedule_interval="0 2 * * *",
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
) as dag:

    dump = BashOperator(
        task_id="pg_dump",
        bash_command=(
            "docker compose -f /home/user/Projects/car-market-place/docker-compose.yml "
            "exec -T postgres pg_dump -U marketplace_user -F c -b postgres "
            "> /home/user/backups/car_marketplace_$(date +%F).dump"
        ),
    )

    rotate = BashOperator(
        task_id="rotate_old_dumps",
        bash_command="find /home/user/backups/ -name 'car_marketplace_*.dump' -mtime +14 -delete",
    )

    dump >> rotate
```

---

## Restore Procedure

### Restore the database from a `.dump` file

```bash
# 1. Copy dump into the running postgres container
docker cp car_marketplace_2026-06-21.dump \
  $(docker compose ps -q postgres):/tmp/restore.dump

# 2. Drop and recreate the schema (WARNING: destroys current data)
docker compose exec postgres psql -U marketplace_user postgres -c \
  "DROP SCHEMA marketplace CASCADE; CREATE SCHEMA marketplace;"

# 3. Restore
docker compose exec postgres pg_restore \
  -U marketplace_user -d postgres -F c --schema=marketplace \
  /tmp/restore.dump

# 4. Verify
docker compose exec postgres psql -U marketplace_user postgres -c \
  "SELECT COUNT(*) FROM marketplace.cars;"
```

### Restore `.env` files

```bash
tar -xzf settings_2026-06-21.tar.gz -C /
# Files will be restored to their original absolute paths
```

---

## Backup Checklist (What to Back Up)

| Item | Location on server | Method | Frequency |
|---|---|---|---|
| PostgreSQL data | Docker volume `pg_data` | `pg_dump` → `/home/user/backups/` | Daily |
| Django `.env` | `backend/car_marketplace/.env` | `tar` → `/home/user/backups/` | On change or weekly |
| DB `.env` | `db/.env` | `tar` → `/home/user/backups/` | On change |
| Telegram bot `.env` | `tg_bot/.env` | `tar` → `/home/user/backups/` | On change |
| ML models | `ml_api/models/*.pkl` | Already in git or rsync | On model update |
| Grafana data | Docker volume `grafana_data` | `docker run --volumes-from … tar` | Weekly |
| Airflow logs | `airflow/logs/` | rsync or logrotate | Weekly |

---

## Quick Reference — Key Servers

| Name | Address | Role |
|---|---|---|
| Production (remote) | `100.69.53.111` | Main running server |
| Local server | `192.168.100.113` | Dev/staging server |
| DB port (internal) | `5432` | Inside Docker network |
| DB port (host-mapped) | `5433` | From host machine |
