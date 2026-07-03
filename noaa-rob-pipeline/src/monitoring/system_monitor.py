import os
import time
import socket
import psutil
import psycopg2
from datetime import datetime, timezone

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "noaa_rob")
POSTGRES_USER = os.getenv("POSTGRES_USER", "noaa_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "noaa_password")
INTERVAL_SECONDS = int(os.getenv("MONITOR_INTERVAL", "30"))

hostname = socket.gethostname()
net_prev = psutil.net_io_counters()

def get_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        dbname=POSTGRES_DB, user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )

def ensure_table():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id BIGSERIAL PRIMARY KEY,
                hostname VARCHAR(100),
                cpu_percent NUMERIC(6,2),
                cpu_count INTEGER,
                memory_percent NUMERIC(6,2),
                memory_used_mb NUMERIC(10,2),
                memory_total_mb NUMERIC(10,2),
                disk_percent NUMERIC(6,2),
                disk_used_gb NUMERIC(10,2),
                disk_total_gb NUMERIC(10,2),
                net_bytes_sent_mb NUMERIC(10,2),
                net_bytes_recv_mb NUMERIC(10,2),
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[MONITOR] Table check failed: {e}")

def collect_metrics():
    global net_prev
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    mem = psutil.virtual_memory()
    memory_percent = mem.percent
    memory_used_mb = round(mem.used / (1024 * 1024), 2)
    memory_total_mb = round(mem.total / (1024 * 1024), 2)
    disk = psutil.disk_usage('/')
    disk_percent = disk.percent
    disk_used_gb = round(disk.used / (1024 ** 3), 2)
    disk_total_gb = round(disk.total / (1024 ** 3), 2)
    net_now = psutil.net_io_counters()
    net_bytes_sent_mb = round((net_now.bytes_sent - net_prev.bytes_sent) / (1024 * 1024), 4)
    net_bytes_recv_mb = round((net_now.bytes_recv - net_prev.bytes_recv) / (1024 * 1024), 4)
    net_prev = net_now
    return (hostname, cpu_percent, cpu_count, memory_percent, memory_used_mb,
            memory_total_mb, disk_percent, disk_used_gb, disk_total_gb,
            net_bytes_sent_mb, net_bytes_recv_mb)

def insert_metrics(metrics):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO system_metrics
                (hostname, cpu_percent, cpu_count, memory_percent, memory_used_mb,
                 memory_total_mb, disk_percent, disk_used_gb, disk_total_gb,
                 net_bytes_sent_mb, net_bytes_recv_mb)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, metrics)
        conn.commit()
        cur.close()
        conn.close()
        print(f"[MONITOR] Inserted at {datetime.now(timezone.utc).isoformat()}")
    except Exception as e:
        print(f"[MONITOR] Insert failed: {e}")

if __name__ == "__main__":
    print(f"[MONITOR] Starting system monitor on {hostname}, interval={INTERVAL_SECONDS}s")
    ensure_table()
    time.sleep(2)
    while True:
        metrics = collect_metrics()
        insert_metrics(metrics)
        time.sleep(INTERVAL_SECONDS)
