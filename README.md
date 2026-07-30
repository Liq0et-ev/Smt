# COVID-19 Data Integration, Analysis, and Visualization Platform

Capstone project: an end-to-end analytics platform built on **Snowflake**
(structured COVID-19 data from the Snowflake Marketplace + augmented
demographic/economic data, transformed with **dbt** following **Medallion
Architecture** — Bronze/Silver/Gold), **MongoDB** (supplementary
semi-structured data: annotations/comments), a **FastAPI** backend, and an
interactive **Dash/Plotly** dashboard with forecasting and clustering.

> Status: work in progress — being built incrementally, task by task.
> See [`docs/tasks/`](docs/tasks/) for a write-up of each task as it lands,
> and [`docs/PROGRESS.md`](docs/PROGRESS.md) for the overall checklist.

## Repository layout (grows as tasks land)

```
sql/                  Snowflake DDL/DML: setup, resource monitors, EDA,
                       optimization, MATCH_RECOGNIZE pattern queries
etl/                   Python ingestion scripts (Bronze layer)
transform/             dbt project: Silver (staging) + Gold (marts) models
eda/                   Automated EDA tooling
common/                Shared Snowflake/env config used across etl/eda/api/dashboard
docs/tasks/            One write-up per assignment task
docs/PROGRESS.md        Checklist of the 10 assignment tasks
```

## Architecture: Medallion (Bronze / Silver / Gold)

```
Snowflake Marketplace ─┐
  (JHU_COVID_19,        ├──▶  dbt staging  ──▶  dbt marts  ──▶  FastAPI  ──▶  Dash dashboard
   WHO_SITUATION_REPORTS│      (SILVER)          (GOLD)          (Task 4)      (Task 5)
   OWID_VACCINATIONS,   │
   DATABANK_DEMOGRAPHICS)
                         │
Our World in Data ───▶ Python ETL ──▶ BRONZE
 (economic/health-system  (etl/augment_country_indicators.py)
  indicators only --
  population already
  native via DATABANK_DEMOGRAPHICS)
```

Table selection is deliberately a lean 4-table subset ("Option C") out of
the 44 available in the Marketplace dataset — see
[`docs/tasks/task1_marketplace_and_resource_monitors.md`](docs/tasks/task1_marketplace_and_resource_monitors.md#core-tables-selected-for-this-project-option-c--lean-set)
for the reasoning and the full 44-table catalog.

- **Bronze** (`COVID19_PLATFORM.BRONZE`): raw external data, as ingested by
  Python — currently `COUNTRY_INDICATORS` (Our World in Data).
- **Silver** (`COVID19_PLATFORM.SILVER`): cleaned/renamed/filtered tables,
  built by dbt staging models directly from the Marketplace source tables
  and Bronze.
- **Gold** (`COVID19_PLATFORM.GOLD`): joined, business-level marts (e.g.
  `country_daily_enriched`) — what the API and dashboard actually query —
  plus forecasting/clustering output (Task 6).

See [`transform/README.md`](transform/README.md) for how to run dbt.

## Task 1 — Snowflake Marketplace dataset + resource monitors ✅

See [`docs/tasks/task1_marketplace_and_resource_monitors.md`](docs/tasks/task1_marketplace_and_resource_monitors.md)
for full write-up (including the full 44-table inventory). Summary:

1. Acquired the free **"COVID-19 Epidemiological Data"** dataset (by
   Starschema) from the Snowflake Marketplace via Snowsight — installed as
   `COVID19_EPIDEMIOLOGICAL_DATA` (44 tables).
2. Ran [`sql/00_setup_warehouse_and_db.sql`](sql/00_setup_warehouse_and_db.sql)
   to create a cost-controlled warehouse (`COVID_WH`, XSMALL, auto-suspend)
   and working database (`COVID19_PLATFORM`) with Bronze/Silver/Gold schemas.
3. Ran [`sql/02_resource_monitors.sql`](sql/02_resource_monitors.sql) to
   create a project-scoped resource monitor (`COVID_WH_MONITOR`, 5
   credits/day) attached to `COVID_WH`, layered on top of Snowflake trial's
   pre-existing account-level monitors (`DAILY_MONITORING`,
   `MONTHLY_MONITORING`).

## Task 2 — Data Exploration and Enhancement ✅

See [`docs/tasks/task2_data_exploration_and_enhancement.md`](docs/tasks/task2_data_exploration_and_enhancement.md).
SQL-based EDA, Python augmentation into Bronze, dbt transformation into
Silver/Gold, and an automated EDA profiler — **fully verified against
live data**: Tier 1 survey (43 tables), Bronze augmentation (234
country indicators), `dbt run`/`dbt test` (7/7 models, 18/18 tests
passing). The Python connector originally rejected both password and
key-pair auth with a generic error; root-caused to
`snowflake-connector-python` needing `authenticator="SNOWFLAKE_JWT"`
passed explicitly alongside `private_key` (not auto-detected). Testing
against live data also surfaced and fixed two real data-quality issues
(a duplicate demographics row, and name-spelling duplicates in
JHU/OWID that were fanning out a join) — see the task doc for details.

## Task 3 — NoSQL (MongoDB) schema design ✅

See [`docs/tasks/task3_mongodb_schema.md`](docs/tasks/task3_mongodb_schema.md).
Three collections (`annotations`, `supplementary_sources`,
`user_preferences`) with `$jsonSchema` validators and indexes
([`mongo/init_collections.py`](mongo/init_collections.py)), plus a CRUD
helper ([`mongo/client.py`](mongo/client.py)) the API (Task 4) will reuse.
Runs entirely via local Docker (`docker-compose.yml`) — no dependency on
Snowflake or the Task 2 connector issue.

## Task 7 — Snowflake Performance Optimization ✅

See [`docs/tasks/task7_performance_optimization.md`](docs/tasks/task7_performance_optimization.md).
Self-contained SQL ([`sql/05_performance_optimization.sql`](sql/05_performance_optimization.sql))
runnable directly in Snowsight: builds a pre-pivoted country-level copy of
`JHU_COVID_19` (since the Marketplace share itself is read-only and can't
be altered), adds a clustering key on `(ISO_CODE, REPORT_DATE)`, and a
materialized view for a common dashboard aggregate — with before/after
query profiling to demonstrate the effect.

## Task 9 — Pattern Recognition (`MATCH_RECOGNIZE`) ✅

See [`docs/tasks/task9_pattern_recognition.md`](docs/tasks/task9_pattern_recognition.md).
Self-contained SQL ([`sql/06_pattern_recognition_match_recognize.sql`](sql/06_pattern_recognition_match_recognize.sql))
runnable directly in Snowsight: automatic per-country "wave" detection
(sustained rise then fall in smoothed daily new cases) and rapid-growth
surge detection, both via `MATCH_RECOGNIZE`.

Further setup/deployment instructions (env vars, running the API/dashboard)
will be added here as those pieces land.
