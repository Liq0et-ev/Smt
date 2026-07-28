# Task 2 — Data Exploration and Enhancement

## What this task delivers

1. **SQL-based EDA** ([`sql/03_eda_structure.sql`](../../sql/03_eda_structure.sql))
   — structure, coverage, duplicates, missing-date gaps, and cross-table
   consistency checks run directly in Snowflake (server-side, no data
   pulled out).
2. **Python + Snowflake augmentation**
   ([`etl/augment_country_indicators.py`](../../etl/augment_country_indicators.py))
   — enriches the dataset with country-level demographic/economic
   indicators (population, median age, GDP per capita, hospital beds per
   thousand, human development index, etc.) it doesn't natively have,
   sourced from Our World in Data's public dataset (World Bank/UN backed).
   Loaded into `COVID19_PLATFORM.RAW.COUNTRY_INDICATORS`.
3. **Automated EDA** ([`eda/automated_eda.py`](../../eda/automated_eda.py))
   — a schema-agnostic profiler: point it at any table name and it (a)
   auto-discovers columns from `INFORMATION_SCHEMA` and computes a full
   null/distinct/min-max structural summary server-side, then (b) pulls a
   bounded random sample and generates a `ydata-profiling` HTML report
   (distributions, correlations, missing-value heatmap) — this is how the
   EDA process is automated instead of hand-writing exploration queries
   per table.

## Why augment with external data instead of relying on the built-in `DEMOGRAPHICS` table

Task 1's exploration found `COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.DEMOGRAPHICS`
is **US-county-level only** (columns: `STATE, COUNTY, TOTAL_POPULATION, ...`).
Since our core epidemiological tables (`JHU_COVID_19`, `ECDC_GLOBAL`) are
country-level and global, that table can't answer "which countries had
higher case rates relative to population/GDP/median age" — hence pulling in
a genuinely external, country-level dataset for real augmentation credit.

## How to run this (on your machine, against your Snowflake account)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: fill in SNOWFLAKE_USER / SNOWFLAKE_PASSWORD at minimum
```

1. **SQL EDA first** — open [`sql/03_eda_structure.sql`](../../sql/03_eda_structure.sql)
   in a Snowsight worksheet, run it (select all → run), and share the
   `DESCRIBE TABLE JHU_COVID_19` + sample-row output back — that table's
   exact schema isn't confirmed yet and the enrichment view in step 3 below
   depends on it.
2. **Augment with external data**:
   ```bash
   python -m etl.augment_country_indicators
   ```
   This downloads OWID's country indicators and loads them into
   `COVID19_PLATFORM.RAW.COUNTRY_INDICATORS`.
3. **Automated EDA**:
   ```bash
   python -m eda.automated_eda --all
   ```
   Produces one HTML report per core table under `reports/eda/`, plus
   printed structural summaries in the terminal.

## Insights (filled in after running against real data)

_To be completed once the EDA/augmentation scripts have run against the
live account — will summarize case/death/vaccination patterns, data
quality gaps found, and correlations between demographic/economic
indicators and outcomes, for the final report._
