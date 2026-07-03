INSERT INTO metadata_table_catalog (table_name, owner_name, description, source_name, refresh_frequency, sensitivity_level, contains_pii)
VALUES
('raw_noaa_hourly_water_level', 'data_engineering_team', 'Raw historical hourly water level data from NOAA CO-OPS API.', 'NOAA CO-OPS API', 'Batch on demand/monthly', 'Public environmental data', FALSE),
('clean_noaa_hourly_water_level', 'data_engineering_team', 'Clean hourly water level data used for feature engineering and training.', 'NOAA CO-OPS API', 'Batch on demand/monthly', 'Public environmental data', FALSE),
('raw_noaa_water_level_stream', 'data_engineering_team', 'Raw near-real-time water level stream from NOAA.', 'NOAA CO-OPS API', 'Every 6 minutes', 'Public environmental data', FALSE),
('hourly_water_level_agg', 'data_engineering_team', 'Hourly aggregation of realtime water level stream.', 'Kafka stream processing', 'Hourly', 'Public environmental data', FALSE),
('prediction_results', 'data_science_team', 'Prediction result for next-hour water level and threshold-based coastal flood risk.', 'Model inference pipeline', 'Hourly', 'Public environmental data', FALSE),
('pipeline_execution_log', 'data_engineering_team', 'Structured execution log for Airflow, batch, stream, training, and prediction pipeline.', 'Internal pipeline', 'Continuous', 'Operational metadata', FALSE),
('data_quality_report', 'data_governance_team', 'Data quality check results for raw, clean, stream, and training data.', 'Internal pipeline', 'Per run', 'Operational metadata', FALSE),
('model_registry', 'data_science_team', 'Model registry containing model versions, metrics, and active model status.', 'Training pipeline', 'Monthly/on demand', 'Operational metadata', FALSE)
ON CONFLICT (table_name) DO UPDATE SET description = EXCLUDED.description;
