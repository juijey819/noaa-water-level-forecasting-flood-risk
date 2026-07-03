import os, json
from datetime import datetime, date
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, text
import pandas as pd

DB_URL = f"postgresql+psycopg2://{os.getenv('POSTGRES_USER','noaa_user')}:{os.getenv('POSTGRES_PASSWORD','noaa_password')}@{os.getenv('POSTGRES_HOST','localhost')}:{os.getenv('POSTGRES_PORT','5432')}/{os.getenv('POSTGRES_DB','noaa_rob')}"
engine = create_engine(DB_URL, pool_pre_ping=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="NOAA ROB Pipeline API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def read_sql(q, params=None):
    with engine.raw_connection() as conn:
        return pd.read_sql_query(q, conn, params=params)


# ── Root ──────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"service": "NOAA ROB Pipeline API", "status": "running"}


# ── Water Level ───────────────────────────────────────────────────────
@app.get("/api/v1/water-level/current")
def current_water_level():
    df = read_sql("SELECT observation_time, water_level_m, sigma, data_flags FROM raw_noaa_water_level_stream ORDER BY observation_time DESC LIMIT 1")
    if df.empty:
        df2 = read_sql("SELECT observation_time, water_level_m, sigma, data_flags, current_risk_level FROM clean_noaa_hourly_water_level ORDER BY observation_time DESC LIMIT 1")
        if df2.empty:
            return {"value": None, "unit": "m", "risk_level": None, "timestamp": None}
        r = df2.iloc[0]
        return {"value": float(r["water_level_m"]), "unit": "m", "risk_level": r["current_risk_level"], "timestamp": str(r["observation_time"]), "sigma": float(r["sigma"]) if pd.notna(r.get("sigma")) else None}
    r = df.iloc[0]
    risk_df = read_sql("SELECT current_risk_level FROM clean_noaa_hourly_water_level ORDER BY observation_time DESC LIMIT 1")
    risk_level = risk_df.iloc[0]["current_risk_level"] if not risk_df.empty else "NORMAL"
    return {"value": float(r["water_level_m"]), "unit": "m", "risk_level": risk_level, "timestamp": str(r["observation_time"]), "sigma": float(r["sigma"]) if pd.notna(r.get("sigma")) else None, "source": "raw_stream"}


@app.get("/api/v1/water-level/historical")
def historical_water_level(days: int = Query(60, ge=1, le=1825)):
    df = read_sql("SELECT observation_time, water_level_m, current_risk_level FROM clean_noaa_hourly_water_level WHERE observation_time >= NOW() - INTERVAL '%(days)s days' ORDER BY observation_time", {"days": days})
    return {"data": [{"date": str(r["observation_time"]), "level": float(r["water_level_m"]), "risk": r["current_risk_level"]} for _, r in df.iterrows()]} if not df.empty else {"data": []}


@app.get("/api/v1/water-level/monthly-average")
def monthly_average_water_level():
    df = read_sql("SELECT EXTRACT(MONTH FROM observation_time) AS month, AVG(water_level_m) AS avg_level FROM clean_noaa_hourly_water_level GROUP BY month ORDER BY month")
    if df.empty:
        return {"data": []}
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return {"data": [{"month": months[int(r["month"])-1], "avg": round(float(r["avg_level"]), 4)} for _, r in df.iterrows()]}


@app.get("/api/v1/water-level/hourly-average")
def hourly_average_water_level():
    df = read_sql("SELECT EXTRACT(HOUR FROM observation_time) AS hour, AVG(water_level_m) AS avg_level FROM clean_noaa_hourly_water_level GROUP BY hour ORDER BY hour")
    if df.empty:
        return {"data": []}
    return {"data": [{"hour": f"{int(r['hour']):02d}:00", "avg": round(float(r["avg_level"]), 4)} for _, r in df.iterrows()]}


# ── Predictions ───────────────────────────────────────────────────────
@app.get("/api/v1/predictions/recent")
def recent_predictions(limit: int = Query(50, ge=1, le=1000)):
    df = read_sql("SELECT * FROM prediction_results ORDER BY prediction_time DESC LIMIT %(limit)s", {"limit": limit})
    if df.empty:
        return {"data": []}
    return {"data": [{k: (str(v) if isinstance(v, (datetime, date)) else float(v) if isinstance(v, (int, float)) else v) for k, v in r.items() if k != "id"} for _, r in df.iterrows()]}


@app.get("/api/v1/predictions/next")
def next_prediction():
    df = read_sql("SELECT prediction_time, target_time, predicted_water_level_next_1h_m, predicted_risk_level, current_water_level_m, model_version FROM prediction_results ORDER BY prediction_time DESC LIMIT 1")
    if df.empty:
        return {"value": None, "risk": None, "current": None, "target_time": None, "model_version": None}
    r = df.iloc[0]
    return {"value": float(r["predicted_water_level_next_1h_m"]), "risk": r["predicted_risk_level"], "current": float(r["current_water_level_m"]), "target_time": str(r["target_time"]), "prediction_time": str(r["prediction_time"]), "model_version": r["model_version"]}


@app.get("/api/v1/predictions/vs-actual")
def predictions_vs_actual(days: int = Query(30, ge=1, le=1825)):
    df = read_sql("""
        SELECT pr.prediction_time, pr.current_water_level_m,
               pr.predicted_water_level_next_1h_m, pr.target_time,
               pr.predicted_risk_level,
               cw.water_level_m AS actual_water_level_m
        FROM prediction_results pr
        LEFT JOIN clean_noaa_hourly_water_level cw
          ON cw.observation_time >= pr.target_time - INTERVAL '15 minutes'
         AND cw.observation_time <= pr.target_time + INTERVAL '15 minutes'
        WHERE pr.prediction_time >= NOW() - INTERVAL '%(days)s days'
        ORDER BY pr.prediction_time
    """, {"days": days})
    if df.empty:
        return {"data": []}
    return {"data": [{"prediction_time": str(r["prediction_time"]), "target_time": str(r["target_time"]), "current": float(r["current_water_level_m"]), "predicted": float(r["predicted_water_level_next_1h_m"]), "actual": float(r["actual_water_level_m"]) if pd.notna(r.get("actual_water_level_m")) else None, "risk": r["predicted_risk_level"]} for _, r in df.iterrows()]}


# ── Risk ──────────────────────────────────────────────────────────────
THRESHOLDS = [
    {"level": "MINOR", "min": 0.534, "max": 0.825},
    {"level": "MODERATE", "min": 0.825, "max": 1.204},
    {"level": "MAJOR", "min": 1.204, "max": None},
]

@app.get("/api/v1/risk/thresholds")
def risk_thresholds():
    return {"data": THRESHOLDS}


@app.get("/api/v1/risk/distribution")
def risk_distribution(days: int = Query(60, ge=1, le=1825)):
    df = read_sql("SELECT current_risk_level, COUNT(*) AS total FROM clean_noaa_hourly_water_level WHERE observation_time >= NOW() - INTERVAL '%(days)s days' GROUP BY current_risk_level ORDER BY total DESC", {"days": days})
    return {"data": [{"name": r["current_risk_level"], "count": int(r["total"])} for _, r in df.iterrows()]} if not df.empty else {"data": []}


# ── Model Registry ────────────────────────────────────────────────────
@app.get("/api/v1/models")
def list_models():
    df = read_sql("SELECT * FROM model_registry ORDER BY created_at DESC")
    if df.empty:
        return {"data": []}
    return {"data": [{k: (str(v) if isinstance(v, (datetime, date)) else float(v) if isinstance(v, (int, float)) and k not in ("id", "train_rows", "test_rows") else int(v) if k in ("train_rows", "test_rows") else v) for k, v in r.items() if k != "id"} for _, r in df.iterrows()]}


@app.get("/api/v1/models/active")
def active_model():
    df = read_sql("SELECT * FROM model_registry WHERE is_active = true ORDER BY created_at DESC LIMIT 1")
    if df.empty:
        return {"version": None, "name": None, "metrics": None}
    r = df.iloc[0]
    return {"version": r["model_version"], "name": r["model_name"], "mae": float(r["mae"]) if pd.notna(r.get("mae")) else None, "rmse": float(r["rmse"]) if pd.notna(r.get("rmse")) else None, "r2": float(r["r2"]) if pd.notna(r.get("r2")) else None, "persistence_mae": float(r["persistence_mae"]) if pd.notna(r.get("persistence_mae")) else None, "improvement": float(r["improvement_vs_persistence"]) if pd.notna(r.get("improvement_vs_persistence")) else None, "status": r["status"], "is_active": bool(r["is_active"])}


# ── Monitoring ────────────────────────────────────────────────────────
@app.get("/api/v1/monitoring/services")
def service_health():
    services = []
    for svc, check_sql in [
        ("PostgreSQL", "SELECT 1 AS ok"),
        ("Airflow", None),
        ("Kafka", None),
        ("PySpark Streaming", None),
        ("FastAPI Backend", None),
    ]:
        ok = False
        if check_sql:
            try:
                read_sql(check_sql)
                ok = True
            except Exception:
                ok = False
        services.append({"name": svc, "status": "healthy" if ok else "unknown", "detail": "connected" if ok else "no check"})
    return {"data": services}


@app.get("/api/v1/monitoring/dags")
def dag_status():
    df = read_sql("SELECT DISTINCT ON (task_name) task_name AS name, status, records_processed AS records, event_time FROM pipeline_execution_log ORDER BY task_name, event_time DESC LIMIT 20")
    if df.empty:
        return {"data": []}
    return {"data": [{"name": r["name"], "status": r["status"], "records": int(r["records"]) if pd.notna(r.get("records")) else 0, "last_run": str(r["event_time"])} for _, r in df.iterrows()]}


@app.get("/api/v1/monitoring/kafka")
def kafka_metrics():
    df = read_sql("SELECT COUNT(*) AS total FROM raw_noaa_water_level_stream")
    total = int(df.iloc[0]["total"]) if not df.empty else 0
    return {"messages_produced": total, "consumer_lag": 0, "topic": os.getenv("KAFKA_TOPIC_RAW", "noaa_water_level_raw")}


@app.get("/api/v1/monitoring/spark")
def spark_metrics():
    raw = read_sql("SELECT COUNT(*) AS total FROM raw_noaa_water_level_stream")
    hourly = read_sql("SELECT COUNT(*) AS total FROM hourly_water_level_agg")
    anomaly = read_sql("SELECT COUNT(*) AS total FROM stream_anomaly_log")
    return {"micro_batches": 0, "raw_rows": int(raw.iloc[0]["total"]) if not raw.empty else 0, "hourly_rows": int(hourly.iloc[0]["total"]) if not hourly.empty else 0, "anomalies": int(anomaly.iloc[0]["total"]) if not anomaly.empty else 0}


@app.get("/api/v1/monitoring/data-quality")
def data_quality():
    df = read_sql("SELECT check_name, status, total_rows, failed_rows, failed_percentage, detail FROM data_quality_report ORDER BY created_at DESC LIMIT 10")
    if df.empty:
        return {"data": []}
    return {"data": [{"label": r["check_name"], "value": f"{r['failed_rows']}/{r['total_rows']}", "ok": r["status"] == "PASSED", "detail": r.get("detail")} for _, r in df.iterrows()]}


# ── Pipeline Logs ─────────────────────────────────────────────────────
@app.get("/api/v1/pipeline/logs")
def pipeline_logs(component: Optional[str] = Query(None), severity: Optional[str] = Query(None), status: Optional[str] = Query(None), q: Optional[str] = Query(None), limit: int = Query(200, ge=1, le=1000)):
    conditions, params = [], {}
    if component:
        conditions.append("component = %(component)s"); params["component"] = component
    if severity:
        conditions.append("severity = %(severity)s"); params["severity"] = severity
    if status:
        conditions.append("status = %(status)s"); params["status"] = status
    if q:
        conditions.append("(message ILIKE %(q)s OR task_name ILIKE %(q)s)"); params["q"] = f"%{q}%"
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    df = read_sql(f"SELECT event_time, pipeline_name, component, task_name, severity, status, message, records_processed FROM pipeline_execution_log {where} ORDER BY event_time DESC LIMIT %(limit)s", {**params, "limit": limit})
    if df.empty:
        return {"data": []}
    return {"data": [{"time": str(r["event_time"]), "pipeline": r["pipeline_name"], "component": r["component"], "task": r["task_name"], "severity": r["severity"], "status": r["status"], "message": r["message"], "records": int(r["records_processed"]) if pd.notna(r.get("records_processed")) else 0} for _, r in df.iterrows()]}


# ── Telegram Notification Sender ──────────────────────────────────────
@app.post("/api/v1/telegram/send")
def send_telegram(message: dict):
    import requests as http
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set"}
    try:
        r = http.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": message.get("text", "")}, timeout=15)
        r.raise_for_status()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
