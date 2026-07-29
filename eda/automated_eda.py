"""Task 2: automated EDA.

Rather than hand-writing bespoke exploration SQL for every one of the 44
Marketplace tables, this module automates the process in two layers:

1. A schema-agnostic SQL profiler: for any given table it reads
   INFORMATION_SCHEMA to discover columns/types, then dynamically builds
   one aggregate query that computes row count, null %, distinct count
   (approximate, for cost/speed on multi-million-row tables) and min/max
   per column -- computed server-side in Snowflake rather than pulling
   raw data over the wire.
2. A visual profiling report (ydata-profiling) built from a bounded,
   server-side SAMPLE of the table, saved as a standalone HTML file --
   distributions, correlations, missing-value heatmaps, etc. -- without
   ever pulling a full multi-million-row table into local memory.

Usage:
    python -m eda.automated_eda --table COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.ECDC_GLOBAL
    python -m eda.automated_eda --all   # profiles every core table listed below
"""
import argparse
import logging
from pathlib import Path

from ydata_profiling import ProfileReport

from common.snowflake_client import query_to_dataframe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "eda"

# Core tables selected in Task 1/2 ("Option C" lean set -- see
# docs/tasks/task1_marketplace_and_resource_monitors.md)
CORE_TABLES = [
    "COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19",
    "COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.WHO_SITUATION_REPORTS",
    "COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.OWID_VACCINATIONS",
    "COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.DATABANK_DEMOGRAPHICS",
]


def _split_table_fqn(table_fqn: str) -> tuple[str, str, str]:
    database, schema, table = table_fqn.split(".")
    return database, schema, table


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
    a full multi-million-row table into memory."""
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
    parser.add_argument("--table", help="Fully-qualified table, e.g. DB.SCHEMA.TABLE")
    parser.add_argument("--all", action="store_true", help="Profile every core table")
    parser.add_argument("--sample-rows", type=int, default=20_000)
    parser.add_argument("--structure-only", action="store_true",
                         help="Skip the visual HTML report, only print the SQL profile summary")
    args = parser.parse_args()

    tables = CORE_TABLES if args.all else ([args.table] if args.table else None)
    if not tables:
        parser.error("Pass --table DB.SCHEMA.TABLE or --all")

    for table_fqn in tables:
        summary = sql_profile_summary(table_fqn)
        print(f"\n=== {table_fqn} structural summary ===")
        print(summary.T)
        if not args.structure_only:
            generate_visual_report(table_fqn, sample_rows=args.sample_rows)


if __name__ == "__main__":
    main()
