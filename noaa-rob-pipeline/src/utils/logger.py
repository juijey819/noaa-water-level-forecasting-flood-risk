import traceback
from datetime import datetime
from src.utils.db import get_psycopg2_connection


def write_pipeline_log(run_id, pipeline_name, component, task_name, severity, status, message, records_processed=0, error_detail=None):
    query = '''
        INSERT INTO pipeline_execution_log
        (run_id, pipeline_name, component, task_name, severity, status, message, records_processed, error_detail, event_time)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    '''
    values = (run_id, pipeline_name, component, task_name, severity, status, message, int(records_processed or 0), error_detail, datetime.utcnow())
    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
        conn.commit()


def log_exception(run_id, pipeline_name, component, task_name, message):
    write_pipeline_log(run_id, pipeline_name, component, task_name, 'FATAL', 'FAILED', message, 0, traceback.format_exc())


def write_audit_log(run_id, pipeline_name, source_name, destination_name, start_time, end_time, records_in, records_out, records_failed, status, executed_by='airflow', error_message=None):
    query = '''
        INSERT INTO pipeline_audit_log
        (run_id, pipeline_name, source_name, destination_name, start_time, end_time, records_in, records_out, records_failed, status, executed_by, error_message)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    '''
    values = (run_id, pipeline_name, source_name, destination_name, start_time, end_time, int(records_in or 0), int(records_out or 0), int(records_failed or 0), status, executed_by, error_message)
    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
        conn.commit()
