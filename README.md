# NOAA Water Level Prediction & Rob Risk Monitoring System

## 1. Ringkasan Project

Project ini adalah sistem data pipeline untuk mengambil, memproses, memprediksi, dan memonitor ketinggian air laut dari **NOAA Tides & Currents API** pada stasiun:

- **Station ID:** `8638610`
- **Station:** Sewells Point, Virginia
- **Wilayah:** Norfolk / Hampton Roads, dekat Elizabeth River dan Chesapeake Bay
- **Datum:** `MHHW`
- **Satuan:** metric

Sistem ini digunakan untuk memprediksi **ketinggian air laut 1 jam ke depan** dan menentukan level risiko rob berdasarkan threshold.

## 2. Tujuan Sistem

- Mengambil data historis dan realtime dari NOAA.
- Menyimpan data hasil batch dan streaming ke PostgreSQL.
- Melakukan data quality check pada data water level.
- Melatih model prediksi secara berkala.
- Melakukan prediksi `water_level_next_1h_m`.
- Menampilkan hasil prediksi dan risiko rob ke dashboard React.
- Menyediakan monitoring pipeline melalui Grafana dan pipeline logs.
- Mengirim notifikasi Telegram untuk update stream dan alert.

## 3. Sumber Data

Data berasal dari **NOAA Tides & Currents API**.

Jenis data yang digunakan:

- **Historical batch:** `hourly_height`
- **Realtime stream:** `water_level`

Data historis digunakan untuk batch processing dan training model. Data realtime digunakan untuk streaming pipeline dan monitoring kondisi terbaru.

## 4. Penjelasan stream

Interval 6 menit digunakan karena data realtime `water_level` dari NOAA tersedia dalam interval sekitar **6 menit**. Jadi producer tidak mengambil data sembarangan setiap detik, tetapi mengikuti frekuensi pembaruan dari penyedia data. Dengan cara ini, pipeline lebih efisien dan data yang dikirim ke Kafka tetap sesuai dengan ritme update NOAA.


## 5. Tech Stack

- **Python**: producer, consumer, prediction script
- **NOAA API**: sumber data water level
- **Apache Airflow**: orkestrasi batch dan training
- **Apache Kafka**: message broker streaming
- **PySpark Structured Streaming**: stream processing
- **PostgreSQL**: data storage utama
- **FastAPI**: backend API
- **React**: frontend dashboard
- **Grafana**: monitoring pipeline dan resource
- **Telegram Bot**: notifikasi stream, prediksi, dan alert
- **Docker Compose**: menjalankan semua service

## 6. Struktur Folder Inti

```text
noaa-rob-pipeline/
├── backend/              # FastAPI backend
├── frontend/             # React frontend
├── dags/                 # Airflow DAG
├── src/
│   ├── batch/            # batch processing
│   ├── streaming/        # producer dan spark streaming
│   ├── training/         # training model
│   ├── prediction/       # prediction consumer
│   └── utils/            # db, logger, telegram
├── sql/                  # schema database
├── models/               # model.pkl
├── grafana/              # dashboard monitoring
├── docker-compose.yml
├── .env.example
└── README.md
```

## 7. Environment Variable

Konfigurasi penting disimpan di file `.env`, misalnya:

```env
POSTGRES_DB=noaa_rob
POSTGRES_USER=noaa_user
POSTGRES_PASSWORD=noaa_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_RAW=noaa_water_level_raw

TELEGRAM_BOT_TOKEN=isi_token_bot
TELEGRAM_CHAT_ID=isi_chat_id
```

## 8. Cara Menjalankan

Masuk ke folder project:

```powershell
cd "C:\Users\LENOVO\Downloads\proj ipbd 2\noaa-rob-pipeline"
```

Salin file environment:

```powershell
copy .env.example .env
```

Jalankan service:

```powershell
docker compose up -d
```

Cek container:

```powershell
docker compose ps
```

Akses aplikasi:

```text
Airflow  : http://localhost:8080
FastAPI  : http://localhost:8000
React    : http://localhost:5173
Grafana  : http://localhost:3000
Postgres : localhost:5433
```

## 9. Airflow DAG

DAG utama yang digunakan:

- `dag_batch_noaa_historical`
  - mengambil data historis NOAA
  - menyimpan raw data
  - transformasi clean data
  - data quality check

- `dag_train_water_level_model`
  - training model beberapa versi
  - menyimpan `model.pkl`
  - mencatat model ke `model_registry`

- DAG retrain bulanan
  - memperbarui model secara berkala
  - menghasilkan model terbaru untuk prediction consumer

## 0. Streaming Pipeline

Producer realtime dijalankan untuk mengambil data NOAA real time:


```powershell
docker compose exec airflow-webserver python scripts/run_producer_loop.py
```


## 12. Training dan Prediction

Training model menggunakan data clean dari PostgreSQL. Model disimpan dalam folder:

```text
models/model.pkl
```

Prediction consumer membaca data terbaru dari PostgreSQL, melakukan feature engineering, mengambil `model.pkl`, lalu menghasilkan prediksi:

```text
water_level_next_1h_m
```

Hasil prediksi disimpan ke tabel:

```text
prediction_results
```

## 13. Dashboard User

Dashboard React menampilkan:

- current water level
- predicted next hour
- current risk
- predicted risk
- flood threshold
- historical water level chart
- risk distribution
- average water level by month
- average water level by hour
- recent predictions

Dashboard ini membantu user memahami kondisi air laut saat ini, tren historis, dan potensi risiko rob satu jam ke depan.

## 14. Monitoring

Grafana digunakan untuk monitoring:

- CPU usage
- RAM usage
- disk usage
- total pipeline logs
- failed tasks
- warnings
- raw data count
- stream messages
- predictions
- anomalies
- records processed
- pipeline logs by severity
- data quality report

Severity log yang digunakan:

```text
INFO, DEBUG, WARNING, FATAL
```

## 15. Data Quality, Metadata, dan Audit

Data quality check meliputi:

- null timestamp
- null water level
- duplicate timestamp
- non-hourly gap
- extreme water level
- high sigma
- data flag warning

Sistem juga memiliki:

- `pipeline_execution_log`
- `data_quality_report`
- `metadata_table_catalog`
- `pipeline_audit_log`

Tabel tersebut digunakan untuk pelacakan proses, dokumentasi tabel, audit trail, dan bukti eksekusi pipeline.

## 16. Notifikasi Telegram

Telegram digunakan untuk mengirim:

- update stream setiap 6 menit
- hasil water level terbaru
- status risiko
- flag/anomaly
- alert pipeline jika terjadi kegagalan

Contoh isi notifikasi:

```text
[NOAA Stream] Station 8638610
Time: 2026-07-03 12:18:00
Water Level: -0.585 m
Risk: NORMAL
Sigma: 0.006
Flags: 1,0,0,0
```

## 17. Command Penting

Cek container:

```powershell
docker compose ps
```

Cek log Kafka:

```powershell
docker logs noaa_kafka --tail=100
```

Cek log PySpark:

```powershell
docker logs noaa_pyspark_streaming --tail=100
```

Cek log backend:

```powershell
docker logs noaa_backend --tail=100
```

Masuk PostgreSQL:

```powershell
docker exec -it noaa_postgres psql -U noaa_user -d noaa_rob
```

Cek jumlah data:

```sql
SELECT COUNT(*) FROM raw_noaa_hourly_water_level;
SELECT COUNT(*) FROM raw_noaa_water_level_stream;
SELECT COUNT(*) FROM prediction_results;
SELECT COUNT(*) FROM pipeline_execution_log;
```
