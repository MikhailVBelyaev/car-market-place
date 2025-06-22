from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="scrape_predict_pipeline",
    default_args=default_args,
    start_date=datetime(2025, 6, 22),
    schedule_interval="@daily",  # run daily
    catchup=False,
) as dag:

    scrape_task = BashOperator(
        task_id="run_scraper",
        bash_command="cd /app/backend && python run_task_lacetti_white.py"
    )
