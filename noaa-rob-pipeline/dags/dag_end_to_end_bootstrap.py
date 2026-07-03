from datetime import datetime
from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.python import PythonOperator
from src.utils.db import read_sql
from src.utils.logger import write_pipeline_log


def check_pipeline_tables(**context):
    checks = {'clean_noaa_hourly_water_level': 'SELECT COUNT(*) AS total FROM clean_noaa_hourly_water_level', 'model_registry': 'SELECT COUNT(*) AS total FROM model_registry', 'pipeline_execution_log': 'SELECT COUNT(*) AS total FROM pipeline_execution_log'}
    for table, query in checks.items():
        total = int(read_sql(query).iloc[0]['total'])
        write_pipeline_log(context['run_id'], 'dag_end_to_end_bootstrap', 'airflow', f'check_{table}', 'INFO' if total > 0 else 'WARNING', 'SUCCESS', f'{table} row count: {total}', total)

with DAG('dag_end_to_end_bootstrap', start_date=datetime(2024,1,1), schedule_interval=None, catchup=False, tags=['noaa','end-to-end']) as dag:
    run_batch = TriggerDagRunOperator(task_id='trigger_batch_historical', trigger_dag_id='dag_batch_noaa_historical', wait_for_completion=True)
    run_training = TriggerDagRunOperator(task_id='trigger_training', trigger_dag_id='dag_train_water_level_model', wait_for_completion=True)
    check_tables = PythonOperator(task_id='check_pipeline_tables', python_callable=check_pipeline_tables, provide_context=True)
    run_batch >> run_training >> check_tables
