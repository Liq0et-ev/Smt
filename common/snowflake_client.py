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


def query_to_dataframe(
    sql: str, config: SnowflakeConfig | None = None, conn=None
) -> pd.DataFrame:
    """Run a query and return a DataFrame, built from plain
    fetchall()/description rather than cursor.fetch_pandas_all(). The
    pandas-native fetch path goes through pyarrow's C extension, which
    has been observed to segfault on very new Python versions (e.g.
    3.14) that pyarrow hasn't fully stabilized against yet -- this is
    slower for huge result sets but far more portable, and every query
    this project runs through here returns a small aggregate/metadata
    result, not raw multi-million-row tables.

    Pass an existing `conn` to reuse a connection across multiple calls
    (e.g. looping over many tables) instead of opening a new one each time.
    """
    def _run(connection):
        cursor = connection.cursor()
        try:
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return pd.DataFrame(rows, columns=columns)
        finally:
            cursor.close()

    if conn is not None:
        return _run(conn)
    with get_connection(config) as connection:
        return _run(connection)


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
