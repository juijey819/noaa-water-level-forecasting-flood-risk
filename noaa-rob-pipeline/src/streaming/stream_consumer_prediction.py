import json, os
from datetime import datetime
import pandas as pd
from kafka import KafkaConsumer
from src.features.feature_engineering import classify_rob_risk, severity_from_risk
from src.models.predict_model import predict_from_hourly_history, save_prediction_result
from src.utils.db import get_engine, upsert_dataframe, read_sql
from src.utils.logger import write_pipeline_log, log_exception
from src.utils.telegram_alert import send_telegram_alert


def build_consumer():
    return KafkaConsumer(os.getenv('KAFKA_TOPIC_RAW', 'noaa_water_level_raw'), bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:29092'), value_deserializer=lambda m: json.loads(m.decode('utf-8')), auto_offset_reset='latest', enable_auto_commit=True, group_id='noaa-stream-consumer')


def save_raw_stream_message(message, topic=None, partition=None, offset=None):
    df = pd.DataFrame([{'station_id': message['station_id'], 'station_name': message.get('station_name'), 'observation_time': pd.to_datetime(message['observation_time']), 'water_level_m': message.get('water_level_m'), 'sigma': message.get('sigma'), 'data_flags': message.get('data_flags'), 'datum': message.get('datum'), 'source_product': message.get('source_product', 'water_level'), 'kafka_topic': topic, 'kafka_partition': partition, 'kafka_offset': offset}])
    upsert_dataframe(df, 'raw_noaa_water_level_stream', 'tmp_raw_noaa_water_level_stream', ['station_id','observation_time','source_product'], ['water_level_m','sigma','data_flags','datum','kafka_topic','kafka_partition','kafka_offset','ingested_at'])


def check_realtime_condition(message):
    station_id = message['station_id']
    obs_time = pd.to_datetime(message['observation_time'])
    current = float(message['water_level_m'])
    prev = read_sql('SELECT water_level_m FROM raw_noaa_water_level_stream WHERE station_id=%(station_id)s AND observation_time < %(obs_time)s ORDER BY observation_time DESC LIMIT 1', {'station_id': station_id, 'obs_time': obs_time})
    previous = None if prev.empty else float(prev.iloc[0]['water_level_m'])
    delta = None if previous is None else abs(current - previous)
    risk = classify_rob_risk(current)
    anomaly = None
    if message.get('data_flags') and message.get('data_flags') != '0,0':
        anomaly = 'DATA_FLAG_WARNING'
    elif message.get('sigma') is not None and float(message.get('sigma')) > 0.05:
        anomaly = 'HIGH_SIGMA_WARNING'
    elif delta is not None and delta > 0.30:
        anomaly = 'SPIKE_WARNING'
    elif risk in ['MODERATE', 'MAJOR']:
        anomaly = f'{risk}_CURRENT_RISK'
    if anomaly:
        sev = severity_from_risk(risk)
        pd.DataFrame([{'station_id': station_id, 'observation_time': obs_time, 'water_level_m': current, 'previous_water_level_m': previous, 'delta_m': delta, 'anomaly_type': anomaly, 'severity': sev, 'message': f'{anomaly}: water level {current:.3f} m at {obs_time}'}]).to_sql('stream_anomaly_log', get_engine(), if_exists='append', index=False)
    sev = severity_from_risk(risk)
    flag_txt = message.get('data_flags', '')
    send_telegram_alert(
        f"\U0001F30A [NOAA Stream] Station {station_id}\n"
        f"Time: {obs_time}\n"
        f"Water Level: {current:.3f} m\n"
        f"Risk: {risk}\n"
        f"Anomaly: {anomaly or 'None'}\n"
        f"Sigma: {message.get('sigma', 'N/A')}\n"
        f"Flags: {flag_txt if flag_txt and flag_txt != '0,0' else 'None'}"
    )
    return anomaly


def aggregate_latest_hour(station_id):
    df = read_sql('SELECT station_id, station_name, observation_time, water_level_m FROM raw_noaa_water_level_stream WHERE station_id=%(station_id)s ORDER BY observation_time DESC LIMIT 500', {'station_id': station_id})
    if df.empty:
        return None
    df['observation_time'] = pd.to_datetime(df['observation_time'])
    df['hour_timestamp'] = df['observation_time'].dt.floor('h')
    grouped = df.groupby(['station_id','hour_timestamp']).agg(hourly_last_water_level_m=('water_level_m','last'), hourly_mean_water_level_m=('water_level_m','mean'), hourly_max_water_level_m=('water_level_m','max'), hourly_min_water_level_m=('water_level_m','min'), hourly_std_water_level_m=('water_level_m','std'), record_count=('water_level_m','count')).reset_index()
    grouped['spike_flag'] = (grouped['hourly_max_water_level_m'] - grouped['hourly_min_water_level_m']) > 0.30
    upsert_dataframe(grouped, 'hourly_water_level_agg', 'tmp_hourly_water_level_agg', ['station_id','hour_timestamp'], ['hourly_last_water_level_m','hourly_mean_water_level_m','hourly_max_water_level_m','hourly_min_water_level_m','hourly_std_water_level_m','record_count','spike_flag','created_at'])
    return grouped


def maybe_predict_hourly(station_id):
    hourly = read_sql('SELECT station_id, hour_timestamp AS timestamp, hourly_last_water_level_m AS water_level_m FROM hourly_water_level_agg WHERE station_id=%(station_id)s ORDER BY hour_timestamp', {'station_id': station_id})
    if len(hourly) < 200:
        return None
    hourly['timestamp'] = pd.to_datetime(hourly['timestamp'])
    hourly['water_level_m'] = pd.to_numeric(hourly['water_level_m'], errors='coerce')
    pred = predict_from_hourly_history(hourly)
    save_prediction_result(pred)
    p = pred.iloc[0]
    risk_icon = "\U0001F6A8" if p['predicted_risk_level'] in ('MAJOR', 'MODERATE') else "\U0000270F"
    send_telegram_alert(
        f"{risk_icon} [NOAA Prediction] Next Hour\n"
        f"Station: {p['station_id']}\n"
        f"Current: {p['current_water_level_m']:.3f} m\n"
        f"Predicted: {p['predicted_water_level_next_1h_m']:.3f} m\n"
        f"Risk: {p['predicted_risk_level']}\n"
        f"Target: {p['target_time']}\n"
        f"Alert: {p['alert_policy']}\n"
        f"Action: {p['recommended_action']}"
    )
    return pred


def run_consumer():
    for record in build_consumer():
        run_id = f"stream_consumer_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        msg = record.value
        try:
            save_raw_stream_message(msg, record.topic, record.partition, record.offset)
            print(f"[{datetime.utcnow()}] ✅ Raw saved: {msg['station_id']} @ {msg['observation_time']} = {msg['water_level_m']}m")
            anomaly = check_realtime_condition(msg)
            print(f"[{datetime.utcnow()}] 📤 Telegram sent (risk={anomaly or 'NORMAL'})")
            aggregate_latest_hour(msg['station_id'])
            print(f"[{datetime.utcnow()}] 📊 Hourly agg updated")
            pred = maybe_predict_hourly(msg['station_id'])
            if pred is not None:
                print(f"[{datetime.utcnow()}] 🔮 Prediction: next 1h = {pred.iloc[0]['predicted_water_level_next_1h_m']:.3f}m (risk={pred.iloc[0]['predicted_risk_level']})")
            else:
                print(f"[{datetime.utcnow()}] ⏳ < 200 hourly pts, no prediction yet")
            write_pipeline_log(run_id, 'stream_noaa_water_level', 'kafka_consumer', 'consume_predict', 'WARNING' if anomaly else 'INFO', 'SUCCESS', 'Stream message consumed and processed.', 1)
        except Exception:
            log_exception(run_id, 'stream_noaa_water_level', 'kafka_consumer', 'consume_predict', 'Failed to process Kafka stream message.')

if __name__ == '__main__':
    run_consumer()
