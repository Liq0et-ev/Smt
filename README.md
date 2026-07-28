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

## Task 1 — Snowflake Marketplace dataset + resource monitors

See [`docs/tasks/task1_marketplace_and_resource_monitors.md`](docs/tasks/task1_marketplace_and_resource_monitors.md)
for full instructions. Summary:

1. Get the free **"COVID-19 Epidemiological Data"** dataset (by Starschema)
   from the Snowflake Marketplace via Snowsight (UI step, not scriptable).
2. Run [`sql/00_setup_warehouse_and_db.sql`](sql/00_setup_warehouse_and_db.sql)
   to create a cost-controlled warehouse (`COVID_WH`) and working database
   (`COVID19_PLATFORM`).
3. Run [`sql/02_resource_monitors.sql`](sql/02_resource_monitors.sql) to cap
   credit spend (warehouse-level daily quota + account-level monthly quota)
   so the trial's credits survive the whole build.

Further setup/deployment instructions (Docker Compose, env vars, running the
API/dashboard) will be added here as those pieces land.
