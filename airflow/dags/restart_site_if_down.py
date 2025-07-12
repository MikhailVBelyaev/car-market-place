from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests

default_args = {
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def check_site():
    try:
        r = requests.get("http://129.80.137.29:8080/", timeout=10)
        if r.status_code != 200:
            raise Exception("Site is down.")
    except Exception:
        raise Exception("Health check failed.")

with DAG("check_and_restart_site",
         default_args=default_args,
         start_date=datetime(2023, 1, 1),
         schedule_interval="*/10 * * * *",  # every 10 min
         catchup=False) as dag:

    check_site_health = PythonOperator(
        task_id="check_site_health",
        python_callable=check_site
    )

    restart_remote_script = BashOperator(
        task_id="restart_remote_server",
        bash_command="""
        ssh -i /keys/ssh-key-2025-07-03.key -o StrictHostKeyChecking=no opc@129.80.137.29 'bash restart_p_dj_f_containers_v2.sh'
        """,
        trigger_rule="one_failed"  # only if check_site_health fails
    )

    check_site_health >> restart_remote_script