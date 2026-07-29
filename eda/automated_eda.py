"""Task 2: automated EDA.

Rather than hand-writing bespoke exploration SQL for every one of the 44
Marketplace tables, this module automates the process in three layers:

0. A dataset-wide survey (`--survey`): loops over EVERY table in the
   Marketplace share via INFORMATION_SCHEMA, and for each one that has a
   date/timestamp column, computes row count + date range with a single
   generated query per table. This is the piece plain static SQL can't
   do cleanly (column names differ per table, so it needs a loop, not
   one query) -- it's the Python-side complement to the pure-SQL
   landscape survey in sql/03_eda_structure.sql section 0.
1. A schema-agnostic SQL profiler (`sql_profile_summary`): for any given
   table it reads INFORMATION_SCHEMA to discover columns/types, then
   dynamically builds one aggregate query that computes row count,
   null %, distinct count (approximate, for cost/speed on multi-million-
   row tables) and min/max per column -- computed server-side in
   Snowflake rather than pulling raw data over the wire.
2. A visual profiling report (ydata-profiling) built from a bounded,
   server-side SAMPLE of the table, saved as a standalone HTML file --
   distributions, correlations, missing-value heatmaps, etc. -- without
   ever pulling a full multi-million-row table into local memory.

Usage:
    python -m eda.automated_eda --survey                                          # Tier 1: all 44 tables
    python -m eda.automated_eda --table COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19  # Tier 2: one table
    python -m eda.automated_eda --all                                             # Tier 2: every core table
"""
import argparse
import logging
from pathlib import Path

import pandas as pd

from common.snowflake_client import get_connection, query_to_dataframe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "eda"

MARKETPLACE_DATABASE = "COVID19_EPIDEMIOLOGICAL_DATA"
MARKETPLACE_SCHEMA = "PUBLIC"

# Core tables selected in Task 1/2 ("Option C" lean set -- see
# docs/tasks/task1_marketplace_and_resource_monitors.md)
CORE_TABLES = [
    "COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19",
    "COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.WHO_SITUATION_REPORTS",
    "COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.OWID_VACCINATIONS",
    "COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.DATABANK_DEMOGRAPHICS",
]

DATE_TYPES = ("DATE", "TIMESTAMP_NTZ", "TIMESTAMP_LTZ", "TIMESTAMP_TZ")


def _split_table_fqn(table_fqn: str) -> tuple[str, str, str]:
    database, schema, table = table_fqn.split(".")
    return database, schema, table


def survey_all_tables(
    database: str = MARKETPLACE_DATABASE, schema: str = MARKETPLACE_SCHEMA
) -> pd.DataFrame:
    """Tier 1: dataset-wide landscape survey. For every table in the
    schema, report row count/size (from INFORMATION_SCHEMA metadata --
    free) and, for the first date/timestamp column found (if any), the
    actual min/max date range -- computed with one small generated query
    per table, since date column names differ across tables and can't be
    covered by a single static query. Reuses a single connection for all
    ~44+ queries instead of opening a new one per table."""
    with get_connection() as conn:
        tables_df = query_to_dataframe(
            f"""
            SELECT table_name, row_count, bytes, comment
            FROM {database}.INFORMATION_SCHEMA.TABLES
            WHERE table_schema = '{schema}'
            ORDER BY row_count DESC
            """,
            conn=conn,
        )

        columns_df = query_to_dataframe(
            f"""
            SELECT table_name, column_name, data_type, ordinal_position
            FROM {database}.INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema = '{schema}' AND data_type IN {DATE_TYPES}
            QUALIFY ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY ordinal_position) = 1
            """,
            conn=conn,
        )
        date_col_by_table = dict(zip(columns_df["TABLE_NAME"], columns_df["COLUMN_NAME"]))

        results = []
        for _, row in tables_df.iterrows():
            table = row["TABLE_NAME"]
            record = {
                "table_name": table,
                "row_count": row["ROW_COUNT"],
                "size_mb": round((row["BYTES"] or 0) / 1024 / 1024, 1),
                "date_column": date_col_by_table.get(table),
                "earliest_date": None,
                "latest_date": None,
            }
            if table in date_col_by_table:
                col = date_col_by_table[table]
                logger.info("Scanning date range of %s.%s.%s", database, table, col)
                range_df = query_to_dataframe(
                    f'SELECT MIN("{col}") AS MIN_DATE, MAX("{col}") AS MAX_DATE '
                    f'FROM {database}.{schema}."{table}"',
                    conn=conn,
                )
                record["earliest_date"] = range_df["MIN_DATE"].iloc[0]
                record["latest_date"] = range_df["MAX_DATE"].iloc[0]
            results.append(record)

    survey_df = pd.DataFrame(results)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS_DIR / "dataset_survey.csv"
    survey_df.to_csv(output_path, index=False)
    logger.info("Wrote %s (%d tables)", output_path, len(survey_df))
    return survey_df


def sql_profile_summary(table_fqn: str):
    """Server-side structural/quality profile: row count + per-column
    null %, approx distinct count, min/max -- one query, no raw data
    transferred out of Snowflake."""
    database, schema, table = _split_table_fqn(table_fqn)

    columns_df = query_to_dataframe(
        f"""
        SELECT column_name, data_type
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema = '{schema}' AND table_name = '{table}'
        ORDER BY ordinal_position
        """
    )
    if columns_df.empty:
        raise ValueError(f"No columns found for {table_fqn} -- check the name/permissions.")

    select_parts = ["COUNT(*) AS ROW_COUNT"]
    for _, row in columns_df.iterrows():
        col = row["COLUMN_NAME"]
        dtype = row["DATA_TYPE"]
        select_parts.append(f'COUNT_IF("{col}" IS NULL) AS "{col}__NULLS"')
        select_parts.append(f'APPROX_COUNT_DISTINCT("{col}") AS "{col}__DISTINCT"')
        if dtype in ("DATE", "TIMESTAMP_NTZ", "TIMESTAMP_LTZ", "TIMESTAMP_TZ",
                      "NUMBER", "FLOAT", "INT"):
            select_parts.append(f'MIN("{col}") AS "{col}__MIN"')
            select_parts.append(f'MAX("{col}") AS "{col}__MAX"')

    sql = f"SELECT {', '.join(select_parts)} FROM {table_fqn}"
    logger.info("Profiling structure of %s (%d columns)", table_fqn, len(columns_df))
    return query_to_dataframe(sql)


def generate_visual_report(table_fqn: str, sample_rows: int = 20_000) -> Path:
    """Pull a bounded, server-side random sample and run ydata-profiling
    on it -- gives distribution/correlation visuals without ever loading
    a full multi-million-row table into memory.

    ydata-profiling is an optional dependency (see requirements-optional.txt)
    -- imported here, not at module level, so --survey/--structure-only
    keep working on Python versions it doesn't support yet."""
    try:
        from ydata_profiling import ProfileReport
    except ImportError as e:
        raise ImportError(
            "ydata-profiling isn't installed. Install it with "
            "`pip install -r requirements-optional.txt` (requires Python < 3.13), "
            "or run with --structure-only to skip visual reports."
        ) from e

    database, schema, table = _split_table_fqn(table_fqn)
    logger.info("Sampling %d rows from %s for visual profiling", sample_rows, table_fqn)
    df = query_to_dataframe(f"SELECT * FROM {table_fqn} SAMPLE ({sample_rows} ROWS)")

    profile = ProfileReport(
        df,
        title=f"Automated EDA: {table}",
        explorative=True,
        minimal=len(df) > 50_000,  # keep heavier correlation stats off for very wide samples
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS_DIR / f"{schema}_{table}.html"
    profile.to_file(output_path)
    logger.info("Wrote %s", output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", action="store_true",
                         help="Tier 1: broad landscape survey across all 44 tables")
    parser.add_argument("--table", help="Fully-qualified table, e.g. DB.SCHEMA.TABLE")
    parser.add_argument("--all", action="store_true", help="Tier 2: profile every core table")
    parser.add_argument("--sample-rows", type=int, default=20_000)
    parser.add_argument("--structure-only", action="store_true",
                         help="Skip the visual HTML report, only print the SQL profile summary")
    args = parser.parse_args()

    if args.survey:
        survey_df = survey_all_tables()
        print(f"\n=== Dataset-wide survey ({len(survey_df)} tables) ===")
        print(survey_df.to_string(index=False))
        return

    tables = CORE_TABLES if args.all else ([args.table] if args.table else None)
    if not tables:
        parser.error("Pass --survey, --table DB.SCHEMA.TABLE, or --all")

    for table_fqn in tables:
        summary = sql_profile_summary(table_fqn)
        print(f"\n=== {table_fqn} structural summary ===")
        print(summary.T)
        if not args.structure_only:
            generate_visual_report(table_fqn, sample_rows=args.sample_rows)


if __name__ == "__main__":
    main()
