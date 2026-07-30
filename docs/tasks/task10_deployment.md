# Task 10 — GitHub Repo, README, and Deployment

## What "done" means for this task

The assignment asks for a repo that runs on any machine, not just the
one it was built on. This doc is the single place that walks through
that from a completely clean checkout -- every other task doc explains
*why* its piece works the way it does; this one is just the ordered
*how to actually stand the whole thing up*.

## Prerequisites

- A Snowflake account with the free **"COVID-19 Epidemiological Data"**
  Marketplace dataset acquired (Task 1) -- this is a manual, one-time
  step in Snowsight's UI, not something a script can do for you.
- A Snowflake key pair for authentication (see
  [`docs/tasks/task2_data_exploration_and_enhancement.md`](task2_data_exploration_and_enhancement.md)
  for why key-pair auth, not password).
- Docker + Docker Compose (for MongoDB, and optionally the API/dashboard
  too).
- Python 3.12 (not 3.14 -- see the same Task 2 doc for why; `dbt`'s
  dependency chain needs 3.12 on this project).

## Environment variables

Copy [`.env.example`](../../.env.example) to `.env` and fill in your own
values. Never commit `.env` (it's already gitignored).

| Variable | Purpose |
|---|---|
| `SNOWFLAKE_ACCOUNT` | Connection identifier, e.g. `xzwiguk-ck25170` (Snowsight: Admin > Accounts) -- **not** the account locator |
| `SNOWFLAKE_USER` | Your Snowflake username |
| `SNOWFLAKE_PRIVATE_KEY_PATH` | Path to your `.p8` private key (preferred auth method) |
| `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | Only if you encrypted the key |
| `SNOWFLAKE_ROLE` / `_WAREHOUSE` / `_DATABASE` / `_SCHEMA` | Defaults already match what the setup SQL creates -- only change if you renamed something |
| `SNOWFLAKE_MARKETPLACE_DATABASE` / `_SCHEMA` | Where the acquired Marketplace share lives (`COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC` by default) |
| `MONGO_URI` | `mongodb://localhost:27017` for local dev, `mongodb://mongo:27017` inside Docker Compose (the API container overrides this automatically) |
| `MONGO_DATABASE` | Defaults to `covid_platform` |
| `API_HOST` / `API_PORT` | Defaults to `0.0.0.0:8000` |

## Setup, in order

Each step depends on the one before it -- skipping ahead will just
produce confusing empty-data errors downstream.

**1. Snowflake groundwork (Snowsight, one-time, manual)**
- Acquire the Marketplace dataset (Task 1).
- Run [`sql/00_setup_warehouse_and_db.sql`](../../sql/00_setup_warehouse_and_db.sql)
  -- creates the warehouse and Bronze/Silver/Gold database.
- Run [`sql/02_resource_monitors.sql`](../../sql/02_resource_monitors.sql)
  -- cost-control resource monitor.

**2. Python environment**
```bash
git clone <this-repo>
cd Smt
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your values
```

**3. Bronze augmentation + Silver/Gold transformation**
```bash
python -m etl.augment_country_indicators   # Bronze: OWID indicators
set -a && source .env && set +a            # dbt needs these in the shell env
export DBT_PROFILES_DIR=$(pwd)/transform
cd transform && dbt run && dbt test        # Silver + Gold, 7 models / 18 tests
cd ..
```

**4. Performance optimization + pattern recognition (Snowsight, one-time)**
- Run [`sql/05_performance_optimization.sql`](../../sql/05_performance_optimization.sql)
  (Task 7 -- clustering key, materialized view).
- Run [`sql/06_pattern_recognition_match_recognize.sql`](../../sql/06_pattern_recognition_match_recognize.sql)
  (Task 9 -- standalone wave/surge detection; the API's live `/waves`
  endpoint reuses this pattern, so this step is optional for the app to
  function, but demonstrates the SQL directly).

**5. Run everything else**

Via Docker Compose (recommended -- this is the "runs on any VM" path):
```bash
docker compose up -d --build
docker compose exec api python -m mongo.init_collections   # one-time: creates MongoDB collections/validators/indexes
```
Then open `http://localhost:8050` (dashboard) and `http://localhost:8000/docs` (API).

Or locally, in three separate terminals (useful for development, since
you get to see each process's logs directly):
```bash
# Terminal 1
docker compose up -d mongo
python -m mongo.init_collections   # one-time

# Terminal 2
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3
python -m dashboard.app
```

## Known limitations (see individual task docs for full detail)

- Countries JHU reports at state/province granularity in this
  Marketplace mirror (the US being the clearest example) have
  undercounted case/death totals in `/daily`, `/waves`, and to a lesser
  extent `/summary` -- see `docs/tasks/task4_api_development.md`.
- `GET /daily` and `GET /cross-check` have been observed to
  intermittently 500 for some countries -- not yet root-caused. The
  dashboard degrades gracefully (that one chart goes empty) rather than
  crashing, via the `safe_fetch` wrapper in `dashboard/app.py`.
- Clustering (Task 6's bonus half) and API caching (Task 8) were
  intentionally not built, as a scope decision under a real deadline --
  documented rather than silently skipped.
