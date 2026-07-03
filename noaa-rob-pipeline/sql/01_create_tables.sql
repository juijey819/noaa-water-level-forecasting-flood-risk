CREATE TABLE IF NOT EXISTS raw_noaa_hourly_water_level (
    id BIGSERIAL PRIMARY KEY,
    station_id VARCHAR(20) NOT NULL,
    station_name VARCHAR(100),
    observation_time TIMESTAMP NOT NULL,
    water_level_m NUMERIC(12, 6),
    sigma NUMERIC(12, 6),
    data_flags VARCHAR(20),
    datum VARCHAR(20),
    source_product VARCHAR(50),
    source_period VARCHAR(50),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (station_id, observation_time, source_product)
);

CREATE TABLE IF NOT EXISTS clean_noaa_hourly_water_level (
    id BIGSERIAL PRIMARY KEY,
    station_id VARCHAR(20) NOT NULL,
    station_name VARCHAR(100),
    observation_time TIMESTAMP NOT NULL,
    water_level_m NUMERIC(12, 6) NOT NULL,
    sigma NUMERIC(12, 6),
    data_flags VARCHAR(20),
    datum VARCHAR(20),
    source_product VARCHAR(50),
    source_period VARCHAR(50),
    current_risk_level VARCHAR(20),
    is_valid BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (station_id, observation_time)
);

CREATE TABLE IF NOT EXISTS raw_noaa_water_level_stream (
    id BIGSERIAL PRIMARY KEY,
    station_id VARCHAR(20) NOT NULL,
    station_name VARCHAR(100),
    observation_time TIMESTAMP NOT NULL,
    water_level_m NUMERIC(12, 6),
    sigma NUMERIC(12, 6),
    data_flags VARCHAR(20),
    datum VARCHAR(20),
    source_product VARCHAR(50),
    kafka_topic VARCHAR(100),
    kafka_partition INTEGER,
    kafka_offset BIGINT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stream_anomaly_log (
    id BIGSERIAL PRIMARY KEY,
    station_id VARCHAR(20) NOT NULL,
    observation_time TIMESTAMP NOT NULL,
    water_level_m NUMERIC(12, 6),
    previous_water_level_m NUMERIC(12, 6),
    delta_m NUMERIC(12, 6),
    anomaly_type VARCHAR(100),
    severity VARCHAR(20),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hourly_water_level_agg (
    id BIGSERIAL PRIMARY KEY,
    station_id VARCHAR(20) NOT NULL,
    hour_timestamp TIMESTAMP NOT NULL,
    hourly_last_water_level_m NUMERIC(12, 6),
    hourly_mean_water_level_m NUMERIC(12, 6),
    hourly_max_water_level_m NUMERIC(12, 6),
    hourly_min_water_level_m NUMERIC(12, 6),
    hourly_std_water_level_m NUMERIC(12, 6),
    record_count INTEGER,
    spike_flag BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prediction_results (
    id BIGSERIAL PRIMARY KEY,
    station_id VARCHAR(20) NOT NULL,
    station_name VARCHAR(100),
    prediction_time TIMESTAMP NOT NULL,
    target_time TIMESTAMP NOT NULL,
    current_water_level_m NUMERIC(12, 6),
    predicted_water_level_next_1h_m NUMERIC(12, 6),
    predicted_risk_level VARCHAR(20),
    severity VARCHAR(20),
    recommended_action TEXT,
    alert_policy VARCHAR(50),
    model_version VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (station_id, prediction_time, model_version)
);

CREATE TABLE IF NOT EXISTS data_quality_report (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(100),
    table_name VARCHAR(100),
    check_name VARCHAR(100),
    total_rows INTEGER,
    failed_rows INTEGER,
    failed_percentage NUMERIC(10, 4),
    status VARCHAR(30),
    detail TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_execution_log (
    log_id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(100),
    pipeline_name VARCHAR(100),
    component VARCHAR(100),
    task_name VARCHAR(100),
    severity VARCHAR(20),
    status VARCHAR(30),
    message TEXT,
    records_processed INTEGER DEFAULT 0,
    error_detail TEXT,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(100),
    pipeline_name VARCHAR(100),
    source_name VARCHAR(100),
    destination_name VARCHAR(100),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    records_in INTEGER DEFAULT 0,
    records_out INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    status VARCHAR(30),
    executed_by VARCHAR(100),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metadata_table_catalog (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) UNIQUE,
    owner_name VARCHAR(100),
    description TEXT,
    source_name VARCHAR(100),
    refresh_frequency VARCHAR(100),
    sensitivity_level VARCHAR(50),
    contains_pii BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_registry (
    id BIGSERIAL PRIMARY KEY,
    model_version VARCHAR(100) UNIQUE,
    model_name VARCHAR(100),
    model_path TEXT,
    feature_config_path TEXT,
    train_start_date DATE,
    train_end_date DATE,
    test_start_date DATE,
    test_end_date DATE,
    train_rows INTEGER,
    test_rows INTEGER,
    mae NUMERIC(12, 8),
    rmse NUMERIC(12, 8),
    r2 NUMERIC(12, 8),
    persistence_mae NUMERIC(12, 8),
    improvement_vs_persistence NUMERIC(12, 4),
    status VARCHAR(30),
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS training_metrics_detail (
    id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(100),
    train_mae_m NUMERIC(12, 8),
    test_mae_m NUMERIC(12, 8),
    test_rmse_m NUMERIC(12, 8),
    test_r2 NUMERIC(12, 8),
    overfit_gap_mae_m NUMERIC(12, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id BIGSERIAL PRIMARY KEY,
    hostname VARCHAR(100),
    cpu_percent NUMERIC(6, 2),
    cpu_count INTEGER,
    memory_percent NUMERIC(6, 2),
    memory_used_mb NUMERIC(10, 2),
    memory_total_mb NUMERIC(10, 2),
    disk_percent NUMERIC(6, 2),
    disk_used_gb NUMERIC(10, 2),
    disk_total_gb NUMERIC(10, 2),
    net_bytes_sent_mb NUMERIC(10, 2),
    net_bytes_recv_mb NUMERIC(10, 2),
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
