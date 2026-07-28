# COVID-19 Data Integration, Analysis, and Visualization Platform

Capstone project: an end-to-end analytics platform built on **Snowflake**
(structured COVID-19 data from the Snowflake Marketplace + augmented
demographic/economic data), **MongoDB** (supplementary semi-structured
data: annotations/comments), a **FastAPI** backend, and an interactive
**Dash/Plotly** dashboard with forecasting and clustering.

> Status: work in progress — being built incrementally, task by task.
> See [`docs/tasks/`](docs/tasks/) for a write-up of each task as it lands,
> and [`docs/PROGRESS.md`](docs/PROGRESS.md) for the overall checklist.

## Repository layout (grows as tasks land)

```
sql/                  Snowflake DDL/DML: setup, resource monitors, EDA,
                       optimization, MATCH_RECOGNIZE pattern queries
docs/tasks/            One write-up per assignment task
docs/PROGRESS.md        Checklist of the 10 assignment tasks
```

## Task 1 — Snowflake Marketplace dataset + resource monitors ✅

See [`docs/tasks/task1_marketplace_and_resource_monitors.md`](docs/tasks/task1_marketplace_and_resource_monitors.md)
for full write-up (including the full 44-table inventory). Summary:

1. Acquired the free **"COVID-19 Epidemiological Data"** dataset (by
   Starschema) from the Snowflake Marketplace via Snowsight — installed as
   `COVID19_EPIDEMIOLOGICAL_DATA` (44 tables).
2. Ran [`sql/00_setup_warehouse_and_db.sql`](sql/00_setup_warehouse_and_db.sql)
   to create a cost-controlled warehouse (`COVID_WH`, XSMALL, auto-suspend)
   and working database (`COVID19_PLATFORM`).
3. Ran [`sql/02_resource_monitors.sql`](sql/02_resource_monitors.sql) to
   create a project-scoped resource monitor (`COVID_WH_MONITOR`, 5
   credits/day) attached to `COVID_WH`, layered on top of Snowflake trial's
   pre-existing account-level monitors (`DAILY_MONITORING`,
   `MONTHLY_MONITORING`).

Further setup/deployment instructions (Docker Compose, env vars, running the
API/dashboard) will be added here as those pieces land.
