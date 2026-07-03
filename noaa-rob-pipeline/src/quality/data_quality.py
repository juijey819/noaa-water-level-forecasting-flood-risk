import pandas as pd
from src.utils.db import get_engine
from src.utils.logger import write_pipeline_log


def build_quality_report(df, run_id, table_name):
    rows = []
    def add(name, total, failed, detail):
        pct = (failed / total * 100) if total else 0
        rows.append({'run_id': run_id, 'table_name': table_name, 'check_name': name, 'total_rows': int(total), 'failed_rows': int(failed), 'failed_percentage': round(pct, 4), 'status': 'PASS' if failed == 0 else 'WARNING', 'detail': detail})
    total = len(df)
    add('null_timestamp', total, int(df['timestamp'].isna().sum()), 'Timestamp is required.')
    add('null_water_level', total, int(df['water_level_m'].isna().sum()), 'Water level is required.')
    add('duplicate_timestamp', total, int(df['timestamp'].duplicated().sum()), 'Timestamp should be unique.')
    temp = df.sort_values('timestamp').copy()
    temp['time_diff_hours'] = temp['timestamp'].diff().dt.total_seconds() / 3600
    add('non_hourly_gap', total, int((temp['time_diff_hours'].dropna() != 1).sum()), 'Hourly data should have 1-hour continuity.')
    add('extreme_water_level', total, int(((df['water_level_m'] < -3) | (df['water_level_m'] > 4)).sum()), 'Loose boundary check.')
    if 'data_flags' in df.columns:
        add('non_normal_data_flags', total, int((df['data_flags'].fillna('UNKNOWN') != '0,0').sum()), 'NOAA data flag is not 0,0.')
    if 'sigma' in df.columns:
        add('high_sigma', total, int((df['sigma'].fillna(0) > 0.05).sum()), 'Sigma higher than 0.05 m.')
    return pd.DataFrame(rows)


def run_and_save_quality_report(df, run_id, table_name, pipeline_name):
    report = build_quality_report(df, run_id, table_name)
    report.to_sql('data_quality_report', get_engine(), if_exists='append', index=False)
    warnings = int((report['status'] != 'PASS').sum())
    write_pipeline_log(run_id, pipeline_name, 'data_quality', f'quality_check_{table_name}', 'WARNING' if warnings else 'INFO', 'SUCCESS', f'Data quality finished with {warnings} warning checks.', len(df))
    return report
