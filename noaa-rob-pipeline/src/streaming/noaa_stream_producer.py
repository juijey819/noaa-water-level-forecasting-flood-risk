import json, os, time
from datetime import datetime
from kafka import KafkaProducer
from src.extract.noaa_client import fetch_latest_water_level
from src.features.feature_engineering import standardize_noaa_columns
from src.utils.logger import write_pipeline_log, log_exception

print(f"[PRODUCER] Starting NOAA stream producer (poll every {os.getenv('STREAM_POLL_INTERVAL_SECONDS', '360')}s)")

def build_producer():
    return KafkaProducer(bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:29092'), value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'), key_serializer=lambda v: str(v).encode('utf-8'))


def create_messages(df):
    station_id = os.getenv('NOAA_STATION_ID', '8638610')
    station_name = os.getenv('NOAA_STATION_NAME', 'Sewells Point, VA')
    datum = os.getenv('NOAA_DATUM', 'MHHW')
    clean = standardize_noaa_columns(df)
    messages = []
    for _, row in clean.iterrows():
        messages.append({'station_id': station_id, 'station_name': station_name, 'observation_time': row['timestamp'].isoformat(), 'water_level_m': float(row['water_level_m']), 'sigma': None if 'sigma' not in row or row.get('sigma') is None else float(row.get('sigma')), 'data_flags': row.get('data_flags', None), 'datum': datum, 'source_product': 'water_level', 'ingested_at': datetime.utcnow().isoformat()})
    return messages


def run_once(run_id='stream_producer_manual'):
    topic = os.getenv('KAFKA_TOPIC_RAW', 'noaa_water_level_raw')
    producer = build_producer()
    try:
        messages = create_messages(fetch_latest_water_level())
        print(f"[PRODUCER] {datetime.utcnow().isoformat()} Fetched {len(messages)} messages from NOAA API")
        for i, msg in enumerate(messages):
            producer.send(topic, key=msg['station_id'], value=msg)
            print(f"[PRODUCER]  Sent [{i+1}/{len(messages)}] {msg['station_id']} @ {msg['observation_time']} = {msg['water_level_m']}m")
        producer.flush()
        print(f"[PRODUCER] {datetime.utcnow().isoformat()} Flushed {len(messages)} messages to Kafka topic '{topic}'")
        write_pipeline_log(run_id, 'stream_noaa_water_level', 'kafka_producer', 'poll_noaa_latest', 'INFO', 'SUCCESS', f'Sent {len(messages)} NOAA realtime messages to Kafka.', len(messages))
        return len(messages)
    except Exception as e:
        print(f"[PRODUCER] ERROR: {e}")
        log_exception(run_id, 'stream_noaa_water_level', 'kafka_producer', 'poll_noaa_latest', 'Failed to poll NOAA latest data or send Kafka message.')
        raise


def run_forever(interval_seconds=360):
    print(f"[PRODUCER] Running loop every {interval_seconds}s")
    while True:
        run_id = f"stream_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        print(f"[PRODUCER] === Run {run_id} ===")
        run_once(run_id)
        print(f"[PRODUCER] Sleeping {interval_seconds}s until next poll...")
        time.sleep(interval_seconds)

if __name__ == '__main__':
    run_forever(int(os.getenv('STREAM_POLL_INTERVAL_SECONDS', '360')))
