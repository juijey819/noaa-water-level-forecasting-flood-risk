import json, os, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils.db import get_engine

MODEL_DIR = Path(os.getenv('MODEL_DIR', './models'))
MODEL_VERSION = 'model_v3_2021_2024'

MODEL_PATH = MODEL_DIR / f'{MODEL_VERSION}.pkl'
FEATURE_CONFIG_PATH = MODEL_DIR / f'{MODEL_VERSION}_feature_config.json'
METADATA_PATH = MODEL_DIR / f'{MODEL_VERSION}_metadata.json'


def register_notebook_model(set_active=True):
    if not MODEL_PATH.exists():
        print(f'Error: {MODEL_PATH} not found. Run copy first.')
        sys.exit(1)
    with open(METADATA_PATH, 'r') as f:
        meta = json.load(f)
    m = meta['metrics']
    row = {
        'model_version': MODEL_VERSION,
        'model_name': meta['model_name'],
        'model_path': str(MODEL_PATH.resolve()),
        'feature_config_path': str(FEATURE_CONFIG_PATH.resolve()),
        'train_start_date': '2021-01-01',
        'train_end_date': '2024-12-31',
        'test_start_date': '2025-01-01',
        'test_end_date': '2026-05-31',
        'train_rows': 35064,
        'test_rows': 12384,
        'mae': m.get('test_MAE_m', m.get('MAE_m', 0)),
        'rmse': m.get('test_RMSE_m', m.get('RMSE_m', 0)),
        'r2': m.get('test_R2', m.get('R2', 0)),
        'persistence_mae': meta.get('persistence_baseline_MAE_m', 0),
        'improvement_vs_persistence': meta.get('improvement_vs_persistence_percent', 0),
        'status': 'active' if set_active else 'archived',
        'is_active': bool(set_active)
    }
    engine = get_engine()
    with engine.begin() as conn:
        if set_active:
            conn.exec_driver_sql("UPDATE model_registry SET is_active = false, status = 'archived' WHERE is_active = true")
        pd.DataFrame([row]).to_sql('model_registry', conn, if_exists='append', index=False)
    print(f'Model {MODEL_VERSION} registered in model_registry (active={set_active}).')


if __name__ == '__main__':
    register_notebook_model(set_active=True)
