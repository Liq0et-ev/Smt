# Task 1 — Snowflake Marketplace Dataset + Resource Monitors

## 1. Get the free "COVID-19 Epidemiological Data" dataset from the Marketplace

This step is a UI action in Snowsight (the Marketplace can't be scripted via
plain SQL) — do this once, in your Snowflake trial account:

1. Log in to Snowsight → **Data Products** → **Marketplace** (left sidebar).
2. Search for **"COVID-19 Epidemiological Data"** (published by **Starschema**).
   It is a free, "Get" listing — no cost, no approval wait.
3. Click **Get**. Snowflake lets you rename the database it will create;
   keep the default or name it `COVID19_EPIDEMIOLOGICAL_DATA` (the rest of
   this project assumes that name — adjust `.env` / config if you rename it).
4. Grant the listing's database access to a role that your API/Python code
   will use, e.g.:

   ```sql
   USE ROLE ACCOUNTADMIN;
   GRANT IMPORTED PRIVILEGES ON DATABASE COVID19_EPIDEMIOLOGICAL_DATA TO ROLE SYSADMIN;
   ```

5. Verify it landed correctly:

   ```sql
   SHOW DATABASES LIKE '%COVID%';
   SHOW SCHEMAS IN DATABASE COVID19_EPIDEMIOLOGICAL_DATA;
   SHOW TABLES IN SCHEMA COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC;
   ```

   The Starschema listing typically exposes tables such as
   `JHU_COVID_19`, `CDC_INPATIENT_BEDS_ALL`, `JHU_COVID_19_GOVERNMENT_RESPONSE`,
   `US_GOV_STATE_TESTING`, etc. Table names can vary slightly by version —
   **please run the `SHOW TABLES` query above and paste the output back to me**
   so I can pin the exact table/column names used by every script downstream
   (Task 2 EDA, API queries, dashboard).

> Marketplace listings are hosted by the provider's account and are
> auto-replicated to your account's region on `GET` — you do not need to
> pick Stockholm again here; that only matters for *your own* account/database
> region (set at trial signup).

## 2. Warehouse + working database

Run [`sql/00_setup_warehouse_and_db.sql`](../../sql/00_setup_warehouse_and_db.sql):
creates an auto-suspending `COVID_WH` (XSMALL, 60s auto-suspend) so the
trial's compute credits aren't burned while idle, and a `COVID19_PLATFORM`
database (schemas `RAW`, `ANALYTICS`, `ML`) for everything we produce
ourselves — separate from the read-only Marketplace share.

## 3. Resource monitors

Run [`sql/02_resource_monitors.sql`](../../sql/02_resource_monitors.sql):

| Monitor | Scope | Quota | Frequency | Triggers |
|---|---|---|---|---|
| `COVID_WH_MONITOR` | `COVID_WH` warehouse only | 5 credits | Daily | 50%/75% notify, 90% suspend, 100% suspend immediately |
| `ACCOUNT_MONITOR` | Whole account | 25 credits | Monthly | 50%/75% notify, 90% suspend, 100% suspend immediately |

Rationale: a trial account starts with $400 in credits, but this project
only needs a fraction of that over 4 days — capping spend early prevents an
accidental runaway query (or a forecasting job stuck in a loop) from
draining the trial before the deadline. `SUSPEND` (not `SUSPEND_IMMEDIATE`)
at 90% lets currently running queries finish; 100% is a hard stop.

## What I need back from you

Please run the three scripts above in order (`00` → get the Marketplace
dataset via UI → `02`) in a Snowsight worksheet, then paste back:

1. Output of `SHOW TABLES IN SCHEMA COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC;`
2. Output of `SHOW RESOURCE MONITORS;`
3. Your Snowflake **account identifier** and **region** (e.g. from
   `SELECT CURRENT_ACCOUNT(), CURRENT_REGION();`) — I need this for the
   `.env.example` connection config in later tasks (I will NOT ask for your
   password; we'll use env vars you keep locally/in your own secrets store).

Once I have the real table/column names, I'll move on to Task 2 (EDA SQL +
Python augmentation) against the actual schema instead of assumed names.
