"""
Telegram channel analytics DAG — corrected rotation (2026-07).

Only trustworthy, spec-controlled posts are scheduled. The old rotation
posted `price_movers` (composition-noise, now disabled) on Wednesdays.

Weekly rotation (all like-for-like, median-based, junk-filtered):
  Monday    09:00 → brand_ranking   (market share — pure counting)
  Wednesday 09:00 → best_value      (real below-median deals, last 7 days)
  Friday    09:00 → age_depreciation (per-model median depreciation curve)

Monthly rotation (1st of month, 09:00):
  seasonal_trends       (per-model monthly median — cheapest month to buy)
  mileage_depreciation  ($ lost per 10,000 km, per model)
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner":        "airflow",
    "retries":      1,
    "retry_delay":  timedelta(minutes=10),
}

# Docker-out-of-Docker: Airflow runs the one-shot tg_channel service on the
# host's car-dev stack. Requires /var/run/docker.sock mounted into Airflow
# and the compose file available at /app.
_CMD = "docker compose -f /app/docker-compose.devlocal.yml -p car-dev --profile channel run --rm tg_channel {post}"

_START = datetime(2026, 7, 1)


with DAG(
    dag_id="tg_channel_daily_price",
    default_args=default_args,
    start_date=_START,
    schedule_interval="0 10 * * *",  # every day 10:00
    catchup=False,
    tags=["channel"],
) as dag_daily:
    BashOperator(
        task_id="post_daily_price",
        bash_command=_CMD.format(post="daily_price"),
    )

with DAG(
    dag_id="tg_channel_monday",
    default_args=default_args,
    start_date=_START,
    schedule_interval="0 9 * * 1",   # Monday 09:00
    catchup=False,
    tags=["channel"],
) as dag_mon:
    BashOperator(
        task_id="post_brand_ranking",
        bash_command=_CMD.format(post="brand_ranking"),
    )

with DAG(
    dag_id="tg_channel_wednesday",
    default_args=default_args,
    start_date=_START,
    schedule_interval="0 9 * * 3",   # Wednesday 09:00
    catchup=False,
    tags=["channel"],
) as dag_wed:
    BashOperator(
        task_id="post_best_value",
        bash_command=_CMD.format(post="best_value"),
    )

with DAG(
    dag_id="tg_channel_friday",
    default_args=default_args,
    start_date=_START,
    schedule_interval="0 9 * * 5",   # Friday 09:00
    catchup=False,
    tags=["channel"],
) as dag_fri:
    BashOperator(
        task_id="post_age_depreciation",
        bash_command=_CMD.format(post="age_depreciation"),
    )

with DAG(
    dag_id="tg_channel_monthly_seasonal",
    default_args=default_args,
    start_date=_START,
    schedule_interval="0 9 1 * *",   # 1st of month 09:00
    catchup=False,
    tags=["channel"],
) as dag_seasonal:
    BashOperator(
        task_id="post_seasonal_trends",
        bash_command=_CMD.format(post="seasonal_trends"),
    )

with DAG(
    dag_id="tg_channel_monthly_mileage",
    default_args=default_args,
    start_date=_START,
    schedule_interval="0 9 15 * *",  # 15th of month 09:00
    catchup=False,
    tags=["channel"],
) as dag_mileage:
    BashOperator(
        task_id="post_mileage_depreciation",
        bash_command=_CMD.format(post="mileage_depreciation"),
    )
