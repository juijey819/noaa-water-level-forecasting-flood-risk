from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from src.models.train_model import train_model_version
from src.utils.logger import write_pipeline_log
from src.utils.telegram_alert import send_telegram_alert

TRAINING_RUNS = [
    {'model_version': 'model_v1_2021_2022', 'train_start_date': '2021-01-01', 'train_end_date': '2022-12-31 23:00:00', 'test_start_date': '2023-01-01', 'test_end_date': '2023-12-31 23:00:00', 'set_active': False},
    {'model_version': 'model_v2_2021_2023', 'train_start_date': '2021-01-01', 'train_end_date': '2023-12-31 23:00:00', 'test_start_date': '2024-01-01', 'test_end_date': '2024-12-31 23:00:00', 'set_active': False},
    {'model_version': 'model_v3_2021_2024', 'train_start_date': '2021-01-01', 'train_end_date': '2024-12-31 23:00:00', 'test_start_date': '2025-01-01', 'test_end_date': '2026-05-31 23:00:00', 'set_active': True}
]


def failure_callback(context):
    dag_id, task_id, run_id = context['dag'].dag_id, context['task_instance'].task_id, context['run_id']
    error = str(context.get('exception'))
    write_pipeline_log(run_id, dag_id, 'airflow', task_id, 'FATAL', 'FAILED', 'Airflow training task failed.', 0, error)
    send_telegram_alert(f'FATAL: Training task failed\nDAG: {dag_id}\nTask: {task_id}\nRun ID: {run_id}\nError: {error}')


def success_callback(context):
    dag_id = context['dag'].dag_id
    run_id = context['run_id']
    write_pipeline_log(run_id, dag_id, 'airflow', 'dag_complete', 'INFO', 'SUCCESS', f'Training DAG {dag_id} completed.')
    send_telegram_alert(f'SUCCESS: Training DAG {dag_id} completed\nRun ID: {run_id}')


def make_train_callable(config):
    def _train(**context):
        return train_model_version(run_id=context['run_id'], **config)
    return _train

with DAG('dag_train_water_level_model', start_date=datetime(2024,1,1), schedule_interval=None, catchup=False, on_failure_callback=failure_callback, on_success_callback=success_callback, tags=['noaa','training']) as dag:
    previous = None
    for config in TRAINING_RUNS:
        task = PythonOperator(task_id=f"train_{config['model_version']}", python_callable=make_train_callable(config), provide_context=True)
        if previous:
            previous >> task
        previous = task
