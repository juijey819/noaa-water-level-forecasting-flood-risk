INSERT INTO model_registry (
    model_version, model_name, model_path, feature_config_path,
    train_start_date, train_end_date, test_start_date, test_end_date,
    train_rows, test_rows, mae, rmse, r2,
    persistence_mae, improvement_vs_persistence, status, is_active
) VALUES (
    'model_v3_2021_2024',
    'Linear Regression',
    '/app/models/model_v3_2021_2024.pkl',
    '/app/models/model_v3_2021_2024_feature_config.json',
    '2021-01-01', '2024-12-31',
    '2025-01-01', '2026-05-31',
    35064, 12384,
    0.01574308, 0.02129418, 0.99578917,
    0.11310111, 86.08,
    'active', true
)
ON CONFLICT (model_version) DO UPDATE SET
    is_active = true,
    status = 'active';
