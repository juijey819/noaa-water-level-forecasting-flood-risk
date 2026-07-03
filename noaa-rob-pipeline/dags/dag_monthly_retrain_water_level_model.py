from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from src.load.batch_pipeline import extract_historical_to_raw, transform_raw_to_clean
from src.models.train_model import train_model_version
from src.utils.logger import write_pipeline_log
from src.utils.telegram_alert import send_telegram_alert


def failure_callback(context):
    dag_id, task_id, run_id = context['dag'].dag_id, context['task_instance'].task_id, context['run_id']
    error = str(context.get('exception'))
    write_pipeline_log(run_id, dag_id, 'airflow', task_id, 'FATAL', 'FAILED', 'Monthly retraining failed.', 0, error)
    send_telegram_alert(f'FATAL: Monthly retraining failed\nDAG: {dag_id}\nTask: {task_id}\nRun ID: {run_id}\nError: {error}')


def success_callback(context):
    dag_id = context['dag'].dag_id
    run_id = context['run_id']
    write_pipeline_log(run_id, dag_id, 'airflow', 'dag_complete', 'INFO', 'SUCCESS', f'Monthly retrain DAG {dag_id} completed.')
    send_telegram_alert(f'SUCCESS: Monthly retrain {dag_id} completed\nRun ID: {run_id}')


def refresh_data(**context):
    extract_historical_to_raw(context['run_id'], include_2026=True)
    return transform_raw_to_clean(context['run_id'])


def train_monthly_candidate(**context):
    logical_date = context['logical_date']
    model_version = f"monthly_model_{logical_date.strftime('%Y_%m')}"
    return train_model_version(context['run_id'], model_version, '2021-01-01', '2026-05-31 23:00:00', '2026-01-01', '2026-05-31 23:00:00', set_active=True)

with DAG('dag_monthly_retrain_water_level_model', start_date=datetime(2026,1,5), schedule_interval='0 2 5 * *', catchup=False, on_failure_callback=failure_callback, on_success_callback=success_callback, tags=['noaa','monthly','retraining']) as dag:
    refresh = PythonOperator(task_id='refresh_verified_data', python_callable=refresh_data, provide_context=True)
    train = PythonOperator(task_id='train_monthly_candidate_model', python_callable=train_monthly_candidate, provide_context=True)
    refresh >> train
