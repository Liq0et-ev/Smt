# Task 7 — Performance Optimization

## Why this can't tune the Marketplace tables directly

`COVID19_EPIDEMIOLOGICAL_DATA` is a Marketplace share owned by
Starschema — we only have `IMPORTED PRIVILEGES` (read-only). Clustering
keys, materialized views, and search optimization all require object
ownership, so none of them can be applied to `JHU_COVID_19` itself. This
is the normal situation with any shared/vendor data warehouse table, not
a limitation specific to this project — the realistic pattern is to
build your own purpose-shaped copy of the data you actually query
repeatedly, and optimize that.

## What was done

All in [`sql/05_performance_optimization.sql`](../../sql/05_performance_optimization.sql),
runnable directly in Snowsight (no dependency on the Python
connector/dbt — see Task 2's open connectivity issue):

1. **Baseline query** against the raw `JHU_COVID_19` (9.7M rows, long
   format, requires a `CASE_TYPE` pivot every time) — profiled via
   Snowsight's Query Profile to establish a "before" number.
2. **`GOLD.JHU_COUNTRY_DAILY`** — a pre-pivoted, country-level-only copy
   (same transformation as the dbt `stg_jhu_covid_19` model, done here
   in plain SQL as a stand-in until the connector issue is resolved and
   `dbt run` builds the real version).
3. **Clustering key** on `(ISO_CODE, REPORT_DATE)` — matches exactly how
   the API (Task 4) and dashboard (Task 5) will filter/sort ("country X,
   date range Y"), so Snowflake's automatic micro-partition pruning stays
   effective as the table grows, instead of degrading if data ever loads
   out of order. Verified with `SYSTEM$CLUSTERING_INFORMATION`.
4. **Materialized view** `GOLD.GLOBAL_DAILY_SUMMARY` — pre-aggregates the
   "global daily totals" query the dashboard's top-line chart will run
   on every page load, so repeated reads don't re-scan/re-aggregate the
   base table each time.
5. Documented (not code-demonstrated, see file for reasoning):
   Snowflake's automatic 24h result caching, the warehouse right-sizing
   already done in Task 1 (`COVID_WH` XSMALL + 60s auto-suspend), and
   Search Optimization Service as a known-but-not-enabled lever (ongoing
   credit cost not justified on a resource-monitor-capped trial account).

## Results (fill in after running against the live account)

_To be completed with actual bytes-scanned/partition-pruning numbers
from Snowsight's Query Profile, comparing section 0 (baseline) vs.
section 3 (clustered) of the SQL file — for the final report._
