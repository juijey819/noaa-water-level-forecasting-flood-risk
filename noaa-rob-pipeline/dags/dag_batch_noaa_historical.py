from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from src.load.batch_pipeline import extract_historical_to_raw, transform_raw_to_clean
from src.utils.logger import write_pipeline_log
from src.utils.telegram_alert import send_telegram_alert


def failure_callback(context):
    dag_id, task_id, run_id = context['dag'].dag_id, context['task_instance'].task_id, context['run_id']
    error = str(context.get('exception'))
    write_pipeline_log(run_id, dag_id, 'airflow', task_id, 'FATAL', 'FAILED', 'Airflow task failed.', 0, error)
    send_telegram_alert(f'FATAL: Airflow task failed\nDAG: {dag_id}\nTask: {task_id}\nRun ID: {run_id}\nError: {error}')


def success_callback(context):
    dag_id = context['dag'].dag_id
    run_id = context['run_id']
    write_pipeline_log(run_id, dag_id, 'airflow', 'dag_complete', 'INFO', 'SUCCESS', f'DAG {dag_id} completed successfully.')
    send_telegram_alert(f'SUCCESS: DAG {dag_id} completed\nRun ID: {run_id}')


def extract_task(**context):
    return extract_historical_to_raw(context['run_id'], include_2026=True)


def transform_task(**context):
    return transform_raw_to_clean(context['run_id'])

with DAG('dag_batch_noaa_historical', start_date=datetime(2024,1,1), schedule_interval=None, catchup=False, on_failure_callback=failure_callback, on_success_callback=success_callback, tags=['noaa','batch']) as dag:
    extract = PythonOperator(task_id='extract_noaa_historical_to_raw', python_callable=extract_task, provide_context=True)
    transform = PythonOperator(task_id='transform_raw_to_clean_and_quality', python_callable=transform_task, provide_context=True)
    extract >> transform
