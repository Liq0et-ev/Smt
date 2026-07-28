"""Thin wrapper around the Snowflake Python connector, reused by the ETL
scripts, the automated-EDA tool, and (later) the FastAPI backend."""
from contextlib import contextmanager

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

from common.config import SnowflakeConfig, load_snowflake_config


@contextmanager
def get_connection(config: SnowflakeConfig | None = None):
    config = config or load_snowflake_config()
    conn = snowflake.connector.connect(
        account=config.account,
        user=config.user,
        password=config.password,
        role=config.role,
        warehouse=config.warehouse,
        database=config.database,
        schema=config.schema,
    )
    try:
        yield conn
    finally:
        conn.close()


def query_to_dataframe(sql: str, config: SnowflakeConfig | None = None) -> pd.DataFrame:
    with get_connection(config) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            return cursor.fetch_pandas_all()
        finally:
            cursor.close()


def execute(sql: str, config: SnowflakeConfig | None = None) -> None:
    with get_connection(config) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
        finally:
            cursor.close()


def upload_dataframe(
    df: pd.DataFrame,
    table_name: str,
    database: str,
    schema: str,
    config: SnowflakeConfig | None = None,
    overwrite: bool = True,
) -> None:
    """Create/replace a Snowflake table from a pandas DataFrame. Column
    names are upper-cased first since Snowflake folds unquoted identifiers
    to uppercase and write_pandas otherwise silently mismatches them."""
    df = df.copy()
    df.columns = [c.upper() for c in df.columns]
    with get_connection(config) as conn:
        write_pandas(
            conn,
            df,
            table_name=table_name,
            database=database,
            schema=schema,
            auto_create_table=True,
            overwrite=overwrite,
        )
