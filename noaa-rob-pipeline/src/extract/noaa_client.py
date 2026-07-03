import os
import requests
import pandas as pd

NOAA_API_URL = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter'


def fetch_noaa_data(begin_date=None, end_date=None, product='hourly_height', date=None, station_id=None, datum=None, time_zone=None, units=None):
    params = {
        'station': station_id or os.getenv('NOAA_STATION_ID', '8638610'),
        'product': product,
        'datum': datum or os.getenv('NOAA_DATUM', 'MHHW'),
        'time_zone': time_zone or os.getenv('NOAA_TIME_ZONE', 'gmt'),
        'units': units or os.getenv('NOAA_UNITS', 'metric'),
        'format': 'json',
        'application': 'noaa_rob_pipeline'
    }
    if date:
        params['date'] = date
    else:
        params['begin_date'] = begin_date
        params['end_date'] = end_date
    response = requests.get(NOAA_API_URL, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if 'error' in payload:
        raise ValueError(payload['error'])
    if 'data' not in payload:
        raise ValueError(f'Unexpected NOAA response: {payload.keys()}')
    return pd.DataFrame(payload['data'])


def fetch_hourly_period(begin_date, end_date):
    df = fetch_noaa_data(begin_date=begin_date, end_date=end_date, product='hourly_height')
    df['source_period'] = f'{begin_date}_{end_date}'
    return df


def fetch_latest_water_level():
    df = fetch_noaa_data(date='latest', product='water_level')
    df['source_product'] = 'water_level'
    return df
