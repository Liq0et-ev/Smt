# Task 2 — Data Exploration and Enhancement

## Two-tier EDA strategy

The task says to analyze "the Snowflake COVID-19 dataset" (the whole
44-table share), but building the full pipeline (dbt, API, dashboard) on
all 44 isn't necessary or comfortable to fully own end to end (see the
Option A/B/C discussion in `docs/tasks/task1_marketplace_and_resource_monitors.md`).
So EDA is split into two tiers:

- **Tier 1 — broad landscape survey, all 44 tables.** Cheap, metadata-driven:
  row counts/size/column counts for every table
  ([`sql/03_eda_structure.sql`](../../sql/03_eda_structure.sql) section 0,
  pure SQL against `INFORMATION_SCHEMA`), plus a Python pass
  ([`eda/automated_eda.py`](../../eda/automated_eda.py) `--survey`) that
  finds each table's date column (if any) and computes its actual date
  range — this is the part plain static SQL can't do cleanly, since every
  table names its date column differently, so it needs a loop. Answers
  "structure and patterns" at the whole-dataset level without the cost of
  deep-profiling 44 tables including several multi-million-row ones.
- **Tier 2 — deep dive, the 4 core tables.** Full structural EDA
  (duplicates, nulls, gaps, cross-source consistency —
  `sql/03_eda_structure.sql` sections 1+) and visual profiling
  (`eda/automated_eda.py --all`, ydata-profiling HTML reports) on the
  tables the actual pipeline (dbt, API, dashboard) is built on:
  `JHU_COVID_19`, `WHO_SITUATION_REPORTS`, `OWID_VACCINATIONS`,
  `DATABANK_DEMOGRAPHICS`.

## What this task delivers

1. **SQL-based EDA** ([`sql/03_eda_structure.sql`](../../sql/03_eda_structure.sql))
   — Tier 1 landscape survey plus Tier 2 structure, coverage, duplicates,
   missing-date gaps, and cross-table consistency checks, run directly in
   Snowflake (server-side, no data pulled out).
2. **Python + Snowflake augmentation (Bronze layer)**
   ([`etl/augment_country_indicators.py`](../../etl/augment_country_indicators.py))
   — enriches the dataset with country-level demographic/economic
   indicators (population, median age, GDP per capita, hospital beds per
   thousand, human development index, etc.) it doesn't natively have,
   sourced from Our World in Data's public dataset (World Bank/UN backed).
   Loaded into `COVID19_PLATFORM.BRONZE.COUNTRY_INDICATORS`.
3. **Transformation to Silver/Gold** ([`transform/`](../../transform/), dbt)
   — dbt staging models clean/rename the Marketplace + Bronze sources into
   the **Silver** layer; a mart model (`country_daily_enriched`) joins them
   into the **Gold** layer that the API/dashboard actually query. See
   [`transform/README.md`](../../transform/README.md) for how this maps to
   Medallion Architecture and why dbt (not plain SQL scripts) is used here.
4. **Automated EDA** ([`eda/automated_eda.py`](../../eda/automated_eda.py))
   — a schema-agnostic profiler: point it at any table name and it (a)
   auto-discovers columns from `INFORMATION_SCHEMA` and computes a full
   null/distinct/min-max structural summary server-side, then (b) pulls a
   bounded random sample and generates a `ydata-profiling` HTML report
   (distributions, correlations, missing-value heatmap) — this is how the
   EDA process is automated instead of hand-writing exploration queries
   per table.

## Why augment with external data at all, given `DATABANK_DEMOGRAPHICS` already gives us global population

Task 1's exploration found two similarly-named tables: `DEMOGRAPHICS`
(US-county-level only) and `DATABANK_DEMOGRAPHICS` (confirmed global,
country-level — population by sex). So population itself doesn't need
external augmentation. What's still missing natively: **median age, GDP
per capita, hospital beds per thousand, human development index** —
exactly the indicators needed to ask "did richer/older/better-resourced
countries fare differently?" `etl/augment_country_indicators.py`
deliberately fetches only those, not population, to avoid duplicating a
metric we already have.

## How the EDA quality checks became dbt tests

`sql/03_eda_structure.sql` found (or checks for) duplicate `(country, date)`
rows, null coverage, and negative values. Rather than being one-off queries
someone has to remember to re-run, those checks are now encoded as dbt
schema tests in [`transform/models/staging/_staging.yml`](../../transform/models/staging/_staging.yml)
and [`transform/models/marts/core/_marts.yml`](../../transform/models/marts/core/_marts.yml)
— they run automatically on every `dbt test` and fail the build if a new
data-quality issue shows up.

## Authentication: key-pair, not password

The Python connector rejected password auth on this account with a
generic "incorrect username or password" error, even with a
browser-confirmed-correct password -- never fully root-caused (network
policy and account-level restrictions were the leading theories, but
inconclusive). Rather than keep debugging password auth blind, the
project uses **key-pair authentication** instead, which is also the
standard approach for non-interactive scripts/tools anyway (passwords
are for humans logging into Snowsight; keys are for programs):

```bash
mkdir -p ~/.ssh/snowflake_keys
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out ~/.ssh/snowflake_keys/snowflake_rsa_key.p8 -nocrypt
openssl rsa -in ~/.ssh/snowflake_keys/snowflake_rsa_key.p8 -pubout -out ~/.ssh/snowflake_keys/snowflake_rsa_key.pub
chmod 600 ~/.ssh/snowflake_keys/snowflake_rsa_key.p8
cat ~/.ssh/snowflake_keys/snowflake_rsa_key.pub
```

Copy the base64 body (not the `BEGIN`/`END` lines) from that last
command's output, then in Snowsight:

```sql
ALTER USER <your_username> SET RSA_PUBLIC_KEY='<paste the base64 body>';
DESC USER <your_username>;  -- confirm RSA_PUBLIC_KEY_FP is now set
```

`common/config.py`/`common/snowflake_client.py` and `transform/profiles.yml`
all prefer `SNOWFLAKE_PRIVATE_KEY_PATH` when set (falling back to
`SNOWFLAKE_PASSWORD` if not) -- see `.env.example`.

## How to run this (on your machine, against your Snowflake account)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: fill in SNOWFLAKE_USER and SNOWFLAKE_PRIVATE_KEY_PATH
# (pointing at the .p8 file generated above)
```

1. **SQL EDA first** — open [`sql/03_eda_structure.sql`](../../sql/03_eda_structure.sql)
   in a Snowsight worksheet and run it (select all → run) to see the
   Tier 1 landscape survey plus the Tier 2 duplicate/gap/cross-check
   results against the live account (schemas for all four core tables are
   already confirmed and built into the dbt staging models).
1b. **Tier 1 Python survey** (all 44 tables' date ranges):
   ```bash
   python -m eda.automated_eda --survey
   ```
   Writes `reports/eda/dataset_survey.csv`.
2. **Augment with external data (Bronze)**:
   ```bash
   python -m etl.augment_country_indicators
   ```
   This downloads OWID's country indicators and loads them into
   `COVID19_PLATFORM.BRONZE.COUNTRY_INDICATORS`.
3. **Build Silver/Gold**:
   ```bash
   cd transform
   set -a && source ../.env && set +a
   export DBT_PROFILES_DIR=$(pwd)
   dbt deps && dbt run && dbt test
   ```
4. **Automated EDA (Tier 2, structural summaries only, no extra install needed)**:
   ```bash
   python -m eda.automated_eda --all --structure-only
   ```
   Prints per-table null/distinct/min-max summaries in the terminal.
5. **Optional: visual HTML profiling reports** — needs `ydata-profiling`,
   which is a separate optional dependency (`requirements-optional.txt`)
   because its dependency chain (numba/llvmlite) lags support for very new
   Python versions (e.g. not yet compatible with Python 3.14). If your
   Python is < 3.13:
   ```bash
   pip install -r requirements-optional.txt
   python -m eda.automated_eda --all   # now also writes HTML reports to reports/eda/
   ```
   If you're on a newer Python and don't want to manage a second
   interpreter just for this, skip it — the structural summaries from
   step 4 already cover the null/distinct/gap analysis; the HTML reports
   only add distribution charts and a correlation matrix on top.

## Insights (filled in after running against real data)

_To be completed once the EDA/augmentation/dbt pipeline has run against the
live account — will summarize case/death/vaccination patterns, data
quality gaps found, and correlations between demographic/economic
indicators and outcomes, for the final report._
