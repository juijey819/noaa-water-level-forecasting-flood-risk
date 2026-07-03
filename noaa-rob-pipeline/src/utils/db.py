import os
from contextlib import contextmanager
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text


def get_postgres_url():
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    db = os.getenv('POSTGRES_DB', 'noaa_rob')
    user = os.getenv('POSTGRES_USER', 'noaa_user')
    password = os.getenv('POSTGRES_PASSWORD', 'noaa_password')
    return f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}'


def get_engine():
    return create_engine(get_postgres_url(), pool_pre_ping=True)


@contextmanager
def get_psycopg2_connection():
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'noaa_rob'),
        user=os.getenv('POSTGRES_USER', 'noaa_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'noaa_password')
    )
    try:
        yield conn
    finally:
        conn.close()


def read_sql(query, params=None):
    return pd.read_sql_query(query, get_engine(), params=params)


def upsert_dataframe(df, table_name, temp_table, conflict_cols, update_cols):
    engine = get_engine()
    with engine.begin() as conn:
        df.to_sql(temp_table, conn, if_exists='replace', index=False)
        cols = list(df.columns)
        col_sql = ', '.join(cols)
        conflict_sql = ', '.join(conflict_cols)
        update_sql = ', '.join([f'{c}=EXCLUDED.{c}' for c in update_cols])
        query = f'''
            INSERT INTO {table_name} ({col_sql})
            SELECT {col_sql} FROM {temp_table}
            ON CONFLICT ({conflict_sql}) DO UPDATE SET {update_sql};
            DROP TABLE IF EXISTS {temp_table};
        '''
        conn.execute(text(query))
