import pandas as pd
from pathlib import Path
from src.utils.db import upsert_dataframe

CSV = Path(__file__).resolve().parent.parent / 'notebooks' / 'data' / 'processed' / 'sample_prediction_output.csv'

df = pd.read_csv(CSV, parse_dates=['timestamp'])
df['station_id'] = '8638610'
df['station_name'] = 'Sewells Point, VA'
df = df.rename(columns={
    'timestamp': 'prediction_time',
    'predicted_water_level_next_1h_m': 'predicted_water_level_next_1h_m',
})
df['target_time'] = df['prediction_time'] + pd.Timedelta(hours=1)
df['current_water_level_m'] = df['water_level_m']
df['model_version'] = 'model_v3_2021_2024'
df['severity'] = df['severity'].fillna('INFO')
df['recommended_action'] = df.get('recommended_action', 'Normal monitoring.').fillna('Normal monitoring.')
df['alert_policy'] = df.get('alert_policy', 'NORMAL').fillna('NORMAL')

out = df[['station_id', 'station_name', 'prediction_time', 'target_time',
          'current_water_level_m', 'predicted_water_level_next_1h_m',
          'predicted_risk_level', 'severity', 'recommended_action', 'alert_policy', 'model_version']].copy()
out = out.dropna(subset=['prediction_time', 'predicted_water_level_next_1h_m'])

upsert_dataframe(out, 'prediction_results', 'tmp_prediction_results',
                 ['station_id', 'prediction_time', 'model_version'],
                 ['station_name', 'target_time', 'current_water_level_m',
                  'predicted_water_level_next_1h_m', 'predicted_risk_level',
                  'severity', 'recommended_action', 'alert_policy'])
print(f'Seeded {len(out)} prediction results from notebook output.')
