"""
Telegram channel analytics DAG.

Schedule:
  Monday    09:00 → brand ranking post
  Wednesday 09:00 → price movers post
  Friday    09:00 → weekly digest post
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner":        "airflow",
    "retries":      1,
    "retry_delay":  timedelta(minutes=10),
}

_CMD = "docker compose -f /app/docker-compose.devlocal.yml -p car-dev run --rm tg_channel {post}"

with DAG(
    dag_id="tg_channel_analytics",
    default_args=default_args,
    start_date=datetime(2026, 6, 23),
    schedule_interval=None,   # triggered per-day DAGs below
    catchup=False,
    tags=["channel"],
) as dag:
    pass   # parent dag — children below define actual schedules


with DAG(
    dag_id="tg_channel_monday",
    default_args=default_args,
    start_date=datetime(2026, 6, 23),
    schedule_interval="0 9 * * 1",   # every Monday 09:00
    catchup=False,
    tags=["channel"],
) as dag_mon:
    BashOperator(
        task_id="post_brand_ranking",
        bash_command=_CMD.format(post="monday"),
    )

with DAG(
    dag_id="tg_channel_wednesday",
    default_args=default_args,
    start_date=datetime(2026, 6, 23),
    schedule_interval="0 9 * * 3",   # every Wednesday 09:00
    catchup=False,
    tags=["channel"],
) as dag_wed:
    BashOperator(
        task_id="post_price_movers",
        bash_command=_CMD.format(post="wednesday"),
    )

with DAG(
    dag_id="tg_channel_friday",
    default_args=default_args,
    start_date=datetime(2026, 6, 23),
    schedule_interval="0 9 * * 5",   # every Friday 09:00
    catchup=False,
    tags=["channel"],
) as dag_fri:
    BashOperator(
        task_id="post_weekly_digest",
        bash_command=_CMD.format(post="friday"),
    )
