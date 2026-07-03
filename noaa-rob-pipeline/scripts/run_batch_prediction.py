import pandas as pd
from src.utils.db import get_engine, upsert_dataframe
from src.models.train_model import get_active_model
from src.features.feature_engineering import build_model_dataset, prepare_latest_feature, classify_rob_risk, severity_from_risk, action_from_risk, classify_alert_policy, load_feature_config
import joblib

STATION_ID = '8638610'

def run_batch_prediction():
    active = get_active_model()
    print(f'Using active model: {active["model_version"]} ({active["model_name"]})')

    feature_config = load_feature_config(active['feature_config_path'])
    feature_cols = feature_config['feature_cols']
    model = joblib.load(active['model_path'])

    q = 'SELECT observation_time AS timestamp, water_level_m FROM clean_noaa_hourly_water_level WHERE station_id = %(station_id)s AND is_valid = true ORDER BY observation_time'
    df = pd.read_sql_query(q, get_engine(), params={'station_id': STATION_ID})
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['water_level_m'] = pd.to_numeric(df['water_level_m'], errors='coerce')
    print(f'Loaded {len(df)} clean rows.')

    model_df = build_model_dataset(df)
    print(f'Built model dataset: {len(model_df)} rows.')

    missing = [c for c in feature_cols if c not in model_df.columns]
    if missing:
        print(f'Missing feature columns: {missing}')
        return
    vals = model.predict(model_df[feature_cols])
    print(f'Predicted all {len(vals)} rows in batch.')
    preds = []
    for i in range(len(model_df)):
        row = model_df.iloc[i]
        preds.append({
            'station_id': STATION_ID,
            'station_name': 'Sewells Point, VA',
            'prediction_time': row['timestamp'],
            'target_time': row['timestamp'] + pd.Timedelta(hours=1),
            'current_water_level_m': float(row['water_level_m']),
            'predicted_water_level_next_1h_m': float(vals[i]),
        })

    out = pd.DataFrame(preds)
    out['predicted_risk_level'] = out['predicted_water_level_next_1h_m'].apply(classify_rob_risk)
    out['severity'] = out['predicted_risk_level'].apply(severity_from_risk)
    out['recommended_action'] = out['predicted_risk_level'].apply(action_from_risk)
    out['alert_policy'] = out['predicted_water_level_next_1h_m'].apply(classify_alert_policy)
    out['model_version'] = active['model_version']

    upsert_dataframe(out, 'prediction_results', 'tmp_prediction_results',
                     ['station_id', 'prediction_time', 'model_version'],
                     ['station_name', 'target_time', 'current_water_level_m',
                      'predicted_water_level_next_1h_m', 'predicted_risk_level',
                      'severity', 'recommended_action', 'alert_policy'])
    print(f'Inserted {len(out)} batch predictions into prediction_results.')


if __name__ == '__main__':
    run_batch_prediction()
