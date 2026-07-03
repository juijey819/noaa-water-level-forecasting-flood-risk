import os
from datetime import datetime
import pandas as pd
from src.extract.noaa_client import fetch_hourly_period
from src.features.feature_engineering import standardize_noaa_columns, classify_rob_risk
from src.quality.data_quality import run_and_save_quality_report
from src.utils.db import get_engine, upsert_dataframe
from src.utils.logger import write_pipeline_log, write_audit_log

STATION_ID = os.getenv('NOAA_STATION_ID', '8638610')
STATION_NAME = os.getenv('NOAA_STATION_NAME', 'Sewells Point, VA')
DATUM = os.getenv('NOAA_DATUM', 'MHHW')


def get_default_periods(include_2026=True):
    periods = [('20210101','20211231'),('20220101','20221231'),('20230101','20231231'),('20240101','20241231'),('20250101','20251231')]
    if include_2026:
        periods.append(('20260101','20260630'))
    return periods


def extract_historical_to_raw(run_id, include_2026=True):
    start = datetime.utcnow()
    frames = []
    for begin, end in get_default_periods(include_2026):
        df = fetch_hourly_period(begin, end)
        df['station_id'] = STATION_ID
        df['station_name'] = STATION_NAME
        df['datum'] = DATUM
        df['source_product'] = 'hourly_height'
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    clean = standardize_noaa_columns(raw)
    out = pd.DataFrame({
        'station_id': STATION_ID,
        'station_name': STATION_NAME,
        'observation_time': clean['timestamp'],
        'water_level_m': clean['water_level_m'],
        'sigma': clean.get('sigma'),
        'data_flags': clean.get('data_flags'),
        'datum': DATUM,
        'source_product': 'hourly_height',
        'source_period': raw.get('source_period', pd.Series(['unknown'] * len(raw))).values[:len(clean)]
    })
    upsert_dataframe(out, 'raw_noaa_hourly_water_level', 'tmp_raw_noaa_hourly_water_level', ['station_id','observation_time','source_product'], ['water_level_m','sigma','data_flags','datum','source_period','ingested_at'])
    write_pipeline_log(run_id, 'batch_noaa_historical', 'airflow', 'extract_historical_to_raw', 'INFO', 'SUCCESS', 'Historical NOAA data extracted to raw storage.', len(out))
    write_audit_log(run_id, 'batch_noaa_historical', 'NOAA CO-OPS API', 'raw_noaa_hourly_water_level', start, datetime.utcnow(), len(out), len(out), 0, 'SUCCESS')
    return len(out)


def transform_raw_to_clean(run_id):
    query = '''
        SELECT station_id, station_name, observation_time AS timestamp, water_level_m, sigma, data_flags, datum, source_product, source_period
        FROM raw_noaa_hourly_water_level
        WHERE station_id = %(station_id)s
        ORDER BY observation_time
    '''
    df = pd.read_sql_query(query, get_engine(), params={'station_id': STATION_ID})
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['water_level_m'] = pd.to_numeric(df['water_level_m'], errors='coerce')
    df['sigma'] = pd.to_numeric(df['sigma'], errors='coerce')
    df = df.dropna(subset=['timestamp','water_level_m']).drop_duplicates(subset=['station_id','timestamp'], keep='last').sort_values('timestamp').reset_index(drop=True)
    df['current_risk_level'] = df['water_level_m'].apply(classify_rob_risk)
    df['is_valid'] = True
    out = pd.DataFrame({
        'station_id': df['station_id'],
        'station_name': df['station_name'],
        'observation_time': df['timestamp'],
        'water_level_m': df['water_level_m'],
        'sigma': df['sigma'],
        'data_flags': df['data_flags'],
        'datum': df['datum'],
        'source_product': df['source_product'],
        'source_period': df['source_period'],
        'current_risk_level': df['current_risk_level'],
        'is_valid': df['is_valid']
    })
    upsert_dataframe(out, 'clean_noaa_hourly_water_level', 'tmp_clean_noaa_hourly_water_level', ['station_id','observation_time'], ['water_level_m','sigma','data_flags','datum','source_product','source_period','current_risk_level','is_valid','created_at'])
    run_and_save_quality_report(df, run_id, 'clean_noaa_hourly_water_level', 'batch_noaa_historical')
    write_pipeline_log(run_id, 'batch_noaa_historical', 'airflow', 'transform_raw_to_clean', 'INFO', 'SUCCESS', 'Raw data transformed to clean storage.', len(out))
    return len(out)
