# Transformation layer (dbt)

Builds the **Silver** (cleaned/joined) and **Gold** (consumption-ready)
layers of the Medallion Architecture on top of:
- the Snowflake Marketplace tables (`COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC`), and
- our own **Bronze** table (`COVID19_PLATFORM.BRONZE.COUNTRY_INDICATORS`),
  loaded by [`etl/augment_country_indicators.py`](../etl/augment_country_indicators.py).

```
transform/
  models/
    staging/    -- Silver: 1:1 cleaned/renamed sources, light filtering only
    marts/core/ -- Gold: joined, business-level tables (what the API/dashboard query)
  macros/       -- generate_schema_name override (schemas = literal Bronze/Silver/Gold, no target-prefix concatenation)
  tests/        -- singular (custom SQL) tests, beyond the schema.yml column tests
```

## Setup

```bash
pip install -r ../requirements.txt   # includes dbt-snowflake
cd transform
set -a && source ../.env && set +a   # loads SNOWFLAKE_* env vars into the shell
export DBT_PROFILES_DIR=$(pwd)       # use the committed profiles.yml (env_var()-based, no secrets in it)
dbt deps                             # installs dbt_utils (used for tests)
```

## Run

```bash
dbt run          # builds all Silver views + Gold tables
dbt test         # runs schema tests (not_null, unique combos, accepted ranges)
dbt docs generate && dbt docs serve  # browsable lineage graph + column docs
```

## Why dbt here (vs. plain SQL scripts)

The bootcamp's dbt module covered `ref()`-based modularity, automatic
lineage, and environment-agnostic models -- all directly useful here:
- `ref()` between staging and mart models means the dependency graph
  (source -> staging -> mart) is explicit and dbt runs/tests things in
  the right order automatically instead of us hand-sequencing `.sql` files.
- Schema tests turn the Task 2 EDA findings (duplicate `(country, date)`
  pairs, negative values, null coverage) into a **repeatable, automated
  check** that runs on every `dbt run`/`dbt test`, instead of one-off
  queries someone has to remember to re-run.
- `dbt docs generate` produces the lineage graph/documentation for the
  final report essentially for free.

The Python ETL script (`etl/augment_country_indicators.py`) still owns the
Bronze-layer ingestion step (HTTP fetch from an external API) because dbt
can't reach out to external web endpoints on its own -- that split (Python
for ingestion, dbt for in-warehouse transformation) is standard practice.
