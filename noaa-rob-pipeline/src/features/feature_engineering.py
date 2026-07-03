import json
from pathlib import Path
import numpy as np
import pandas as pd

TIDE_ANCHOR_TIMESTAMP = pd.Timestamp('2021-01-01 00:00:00')
SEMI_DIURNAL_PERIOD_HOURS = 12.42

THRESHOLD_MINOR_M = 0.534
THRESHOLD_MODERATE_M = 0.825
THRESHOLD_MAJOR_M = 1.204


def standardize_noaa_columns(raw):
    df = raw.copy()
    unnamed_cols = [c for c in df.columns if str(c).startswith('Unnamed')]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)
    rename_map = {'t': 'timestamp', 'v': 'water_level_m', 's': 'sigma', 'f': 'data_flags'}
    df = df.rename(columns={old: new for old, new in rename_map.items() if old in df.columns})
    if 'timestamp' not in df.columns or 'water_level_m' not in df.columns:
        raise ValueError('Required columns timestamp/water_level_m are missing.')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['water_level_m'] = pd.to_numeric(df['water_level_m'], errors='coerce')
    if 'sigma' in df.columns:
        df['sigma'] = pd.to_numeric(df['sigma'], errors='coerce')
    df = df.dropna(subset=['timestamp', 'water_level_m'])
    df = df.drop_duplicates(subset=['timestamp'], keep='last')
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def classify_rob_risk(water_level_m):
    if pd.isna(water_level_m):
        return 'UNKNOWN'
    if water_level_m >= THRESHOLD_MAJOR_M:
        return 'MAJOR'
    if water_level_m >= THRESHOLD_MODERATE_M:
        return 'MODERATE'
    if water_level_m >= THRESHOLD_MINOR_M:
        return 'MINOR'
    return 'NORMAL'


def severity_from_risk(risk_level):
    return {'NORMAL':'INFO','MINOR':'WARNING','MODERATE':'WARNING','MAJOR':'FATAL','UNKNOWN':'WARNING'}.get(risk_level, 'WARNING')


def action_from_risk(risk_level):
    return {
        'NORMAL': 'Normal monitoring.',
        'MINOR': 'Monitor low-lying coastal areas.',
        'MODERATE': 'Prepare coastal flood response.',
        'MAJOR': 'Issue urgent warning and activate emergency response.',
        'UNKNOWN': 'Check data quality.'
    }.get(risk_level, 'Check data quality.')


def classify_alert_policy(predicted_water_level_m, buffer_m=0.03):
    if predicted_water_level_m >= THRESHOLD_MAJOR_M:
        return 'MAJOR_ALERT'
    if predicted_water_level_m >= THRESHOLD_MODERATE_M:
        return 'MODERATE_ALERT'
    if predicted_water_level_m >= THRESHOLD_MINOR_M:
        return 'MINOR_ALERT'
    if predicted_water_level_m >= THRESHOLD_MINOR_M - buffer_m:
        return 'NEAR_MINOR_THRESHOLD'
    return 'NORMAL'


def add_time_features(df):
    out = df.copy()
    out['hour_of_day'] = out['timestamp'].dt.hour
    out['day_of_week'] = out['timestamp'].dt.dayofweek
    out['month'] = out['timestamp'].dt.month
    out['day_of_year'] = out['timestamp'].dt.dayofyear
    out['is_weekend'] = out['day_of_week'].isin([5, 6]).astype(int)
    out['hour_sin'] = np.sin(2 * np.pi * out['hour_of_day'] / 24)
    out['hour_cos'] = np.cos(2 * np.pi * out['hour_of_day'] / 24)
    out['doy_sin'] = np.sin(2 * np.pi * out['day_of_year'] / 365.25)
    out['doy_cos'] = np.cos(2 * np.pi * out['day_of_year'] / 365.25)
    hours_from_anchor = (out['timestamp'] - TIDE_ANCHOR_TIMESTAMP).dt.total_seconds() / 3600
    out['semi_diurnal_sin'] = np.sin(2 * np.pi * hours_from_anchor / SEMI_DIURNAL_PERIOD_HOURS)
    out['semi_diurnal_cos'] = np.cos(2 * np.pi * hours_from_anchor / SEMI_DIURNAL_PERIOD_HOURS)
    return out


def add_lag_rolling_features(df):
    out = df.copy()
    for lag in [1, 2, 3, 6, 12, 24, 48, 72, 168]:
        out[f'lag_{lag}h'] = out['water_level_m'].shift(lag)
    shifted = out['water_level_m'].shift(1)
    for window in [3, 6, 12, 24, 48, 168]:
        out[f'rolling_mean_{window}h'] = shifted.rolling(window).mean()
        out[f'rolling_std_{window}h'] = shifted.rolling(window).std()
        out[f'rolling_min_{window}h'] = shifted.rolling(window).min()
        out[f'rolling_max_{window}h'] = shifted.rolling(window).max()
    return out


def build_model_dataset(water_data):
    df = water_data[['timestamp', 'water_level_m']].copy().sort_values('timestamp').reset_index(drop=True)
    df = add_time_features(df)
    df = add_lag_rolling_features(df)
    df['water_level_next_1h_m'] = df['water_level_m'].shift(-1)
    df['actual_risk_level'] = df['water_level_next_1h_m'].apply(classify_rob_risk)
    return df.dropna().reset_index(drop=True)


def get_default_feature_cols(model_df):
    return [c for c in model_df.columns if c not in ['timestamp', 'water_level_next_1h_m', 'actual_risk_level']]


def prepare_latest_feature(hourly_history_df, feature_cols):
    df = hourly_history_df.copy()
    if 't' in df.columns or 'v' in df.columns:
        df = standardize_noaa_columns(df)
    df = df[['timestamp', 'water_level_m']].copy().sort_values('timestamp').reset_index(drop=True)
    df = add_time_features(df)
    df = add_lag_rolling_features(df)
    df = df.dropna().reset_index(drop=True)
    if df.empty:
        raise ValueError('Not enough hourly history to build latest features.')
    latest = df.tail(1).copy()
    missing = [c for c in feature_cols if c not in latest.columns]
    if missing:
        raise ValueError(f'Missing features: {missing}')
    return latest[['timestamp'] + feature_cols]


def load_feature_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
