# Task 1 — Snowflake Marketplace Dataset + Resource Monitors

## 1. Marketplace dataset

Acquired the free **"COVID-19 Epidemiological Data"** listing (published by
**Starschema**, Health and Life Sciences category, "Unlimited Access") from
the Snowflake Marketplace via Snowsight → Data Products → Marketplace →
search "COVID-19" → **Get**.

It installed as database **`COVID19_EPIDEMIOLOGICAL_DATA`**, schema
`PUBLIC`, containing **44 tables**. Full inventory (name, row count, one-line
purpose):

| Table | Rows | Notes |
|---|---|---|
| `JHU_COVID_19` | 9,738,292 | Global case counts (Johns Hopkins) — primary source for Task 2 |
| `JHU_COVID_19_TIMESERIES` | 12,450,699 | JHU data reshaped as time series |
| `JHU_DASHBOARD_COVID_19_GLOBAL` | 4,632 | JHU dashboard snapshot |
| `JHU_VACCINES` | 40,054 | JHU vaccination counts |
| `ECDC_GLOBAL` | 61,900 | European CDC cases/deaths, cols: `COUNTRY_REGION, DATE, CASES, DEATHS` — cross-check source |
| `ECDC_GLOBAL_WEEKLY` | 6,407 | ECDC weekly aggregation |
| `OWID_VACCINATIONS` | 169,179 | Our World in Data vaccination rollout — see schema below |
| `NYT_US_COVID19` | 3,525,161 | US cases/deaths, county level |
| `NYT_US_REOPEN_STATUS` | 52 | US state reopening status |
| `CT_US_COVID_TESTS` | 20,780 | US COVID-19 testing and mortality |
| `CDC_TESTING` | 50,107 | CDC testing data |
| `CDC_REPORTED_PATIENT_IMPACT` | 48,881 | CDC hospital patient impact |
| `CDC_POLICY_MEASURES` | 4,217 | CDC public health policy measures |
| `CDC_INPATIENT_BEDS_ALL` | 1,581 | Hospital bed capacity |
| `CDC_INPATIENT_BEDS_COVID_19` | 1,581 | COVID-occupied beds |
| `CDC_INPATIENT_BEDS_ICU_ALL` | 1,581 | ICU bed capacity |
| `APPLE_MOBILITY` | 3,851,311 | Apple mobility trends (driving/walking/transit) |
| `GOOG_GLOBAL_MOBILITY_REPORT` | 11,730,025 | Google mobility trends (retail, grocery, parks, transit, workplaces, residential) — largest table, good Task 7 optimization candidate |
| `DEMOGRAPHICS` | 3,140 | **US county-level** population by sex (not global — see Task 2 augmentation) |
| `DATABANK_DEMOGRAPHICS` | 216 | Supplementary demographic reference |
| `HDX_ACAPS` | 23,923 | ACAPS international public health measures |
| `HS_BULK_DATA` | 727,762 | Global healthcare providers |
| `HUM_RESTRICTIONS_AIRLINE` | 687 | Travel restrictions by airline |
| `HUM_RESTRICTIONS_COUNTRY` | 235 | Travel restrictions by country |
| `IHME_COVID_19` | 208,406 | IHME projections |
| `KFF_HCP_CAPACITY` | 51 | US healthcare capacity by state (2018) |
| `KFF_US_ICU_BEDS` | 3,142 | US ICU beds |
| `KFF_US_POLICY_ACTIONS` | 51 | US state policy actions |
| `KFF_US_REOPENING_TIMELINE_INCREMENT` | 15,402 | US reopening timeline |
| `KFF_US_STATE_MITIGATIONS` | 51 | US state mitigation measures |
| `METADATA` | 317 | Dataset metadata/data dictionary |
| `NYC_HEALTH_TESTS` | 130,453 | NYC-specific testing |
| `PCM_DPS_COVID19` | 116,088 | Italy case statistics (summary) |
| `PCM_DPS_COVID19_DETAILS` | 29,022 | Italy case statistics (detailed) |
| `RKI_GER_COVID19_DASHBOARD` | 411 | Germany district-level (Robert Koch Institut) |
| `SCS_BE_DETAILED_HOSPITALISATIONS` | 12,595 | Belgium hospitalisations |
| `SCS_BE_DETAILED_MORTALITY` | 11,413 | Belgium mortality |
| `SCS_BE_DETAILED_PROVINCE_CASE_COUNTS` | 236,625 | Belgium/Luxembourg case counts |
| `SCS_BE_DETAILED_TESTS` | 13,908 | Belgium tests |
| `VH_CAN_DETAILED` | 2,338 | Canada cases/deaths, province level |
| `WHO_DAILY_REPORT` | 238 | WHO daily report |
| `WHO_SITUATION_REPORTS` | 30,722 | WHO situation reports |
| `WHO_TIMESERIES` | 238 | WHO time series |

**Core tables selected for this project ("Option C" / lean set)** — chosen
deliberately over using all 44 tables, to keep the project comfortably
scoped while still covering every theme the assignment asks about
(infection, mortality, vaccination, demographics), and because every one
of these four carries `ISO3166_1` natively, avoiding fragile country-name
joins across sources:

| Table | Role |
|---|---|
| `JHU_COVID_19` | Primary global cases/deaths (long-format: one row per country/date/CASE_TYPE) |
| `WHO_SITUATION_REPORTS` | Independent cross-check against JHU (shorter date coverage) |
| `OWID_VACCINATIONS` | Vaccination rollout |
| `DATABANK_DEMOGRAPHICS` | Global, country-level demographics (population by sex) |

Confirmed schemas (via `DESCRIBE TABLE` + sample rows):

- `JHU_COVID_19`: `COUNTRY_REGION, PROVINCE_STATE, COUNTY, FIPS, DATE,
  CASE_TYPE, CASES, LONG, LAT, ISO3166_1, ISO3166_2, DIFFERENCE,
  LAST_UPDATED_DATE, LAST_REPORTED_FLAG`. Long-format: `CASE_TYPE` is
  `'Confirmed'` or `'Deaths'`, `CASES` is the cumulative count for that
  type, `DIFFERENCE` is the daily delta. Mixes country-level rows with
  sub-national (province/county) rows in the same table — must filter to
  `PROVINCE_STATE IS NULL AND COUNTY IS NULL` for country-level analysis.
- `WHO_SITUATION_REPORTS`: `COUNTRY, TOTAL_CASES, CASES_NEW, DEATHS,
  DEATHS_NEW, TRANSMISSION_CLASSIFICATION, DAYS_SINCE_LAST_REPORTED_CASE,
  ISO3166_1, COUNTRY_REGION, DATE, SITUATION_REPORT_NAME,
  SITUATION_REPORT_URL, LAST_UPDATE_DATE, LAST_REPORTED_FLAG`. Wide format
  already (no pivot needed), but only 238 distinct report dates total —
  shorter coverage window than JHU.
- `OWID_VACCINATIONS`: `DATE, COUNTRY_REGION, ISO3166_1,
  TOTAL_VACCINATIONS, PEOPLE_VACCINATED, PEOPLE_FULLY_VACCINATED,
  DAILY_VACCINATIONS_RAW, DAILY_VACCINATIONS,
  TOTAL_VACCINATIONS_PER_HUNDRED, PEOPLE_VACCINATED_PER_HUNDRED,
  PEOPLE_FULLY_VACCINATED_PER_HUNDRED, DAILY_VACCINATIONS_PER_MILLION,
  VACCINES, LAST_OBSERVATION_DATE, SOURCE_NAME, SOURCE_WEBSITE,
  LAST_UPDATE_DATE, LAST_REPORTED_FLAG`.
- `DATABANK_DEMOGRAPHICS`: `ISO3166_1, ISO3166_2, FIPS, LATITUDE,
  LONGITUDE, STATE, COUNTY, TOTAL_POPULATION, TOTAL_MALE_POPULATION,
  TOTAL_FEMALE_POPULATION, COUNTRY_REGION`. Confirmed via sample rows to be
  **global, country-level** (one row per country, `STATE`/`COUNTY` null) —
  distinct from the similarly-named but US-county-only `DEMOGRAPHICS`
  table. Because this gives us global population natively, Task 2's Python
  augmentation ([`etl/augment_country_indicators.py`](../../etl/augment_country_indicators.py))
  deliberately skips re-fetching population and instead adds genuinely
  missing indicators: median age, GDP per capita, hospital beds per
  thousand, human development index.

Tables considered but **not** used in this lean set (available if scope
expands later): `ECDC_GLOBAL`/`ECDC_GLOBAL_WEEKLY` (redundant with
JHU+WHO as case/death sources), `GOOG_GLOBAL_MOBILITY_REPORT`/`APPLE_MOBILITY`
(behavioral data, no mobility angle in this v1), `CDC_INPATIENT_BEDS_*`/
`KFF_*` (US-specific healthcare capacity), and the country-specific
regional tables (`PCM_DPS_COVID19` (Italy), `RKI_GER_COVID19_DASHBOARD`
(Germany), `SCS_BE_*` (Belgium), `VH_CAN_DETAILED` (Canada)) since JHU/WHO
already give global coverage.

## 2. Account setup

- Account identifier: `MA29554`
- Region: `AWS_EU_NORTH_1` (AWS, Stockholm) — confirmed via
  `SELECT CURRENT_ACCOUNT(), CURRENT_REGION();`
- Warehouse `COVID_WH` created (XSMALL, 60s auto-suspend, auto-resume) via
  [`sql/00_setup_warehouse_and_db.sql`](../../sql/00_setup_warehouse_and_db.sql)
- Working database `COVID19_PLATFORM` created, following **Medallion
  Architecture** (Bronze/Silver/Gold, as taught in the bootcamp's
  Databricks/Delta Lake module, implemented here on Snowflake): schemas
  `BRONZE` (raw external data landed by Python), `SILVER` (cleaned/joined,
  built by dbt), `GOLD` (consumption-ready marts, built by dbt). See
  [`transform/README.md`](../../transform/README.md).

## 3. Resource monitors

Ran [`sql/02_resource_monitors.sql`](../../sql/02_resource_monitors.sql) and
verified with `SHOW RESOURCE MONITORS;`:

| Monitor | Scope | Quota | Frequency | Origin |
|---|---|---|---|---|
| `DAILY_MONITORING` | Account | 30 credits | Daily | **Pre-existing** — Snowflake trial default |
| `MONTHLY_MONITORING` | Account (level = `ACCOUNT`) | 380 credits | Monthly | **Pre-existing** — Snowflake trial default |
| `COVID_WH_MONITOR` | `COVID_WH` warehouse only | 5 credits | Daily | **Created for this project** |

Finding worth noting for the report: Snowflake trial accounts already ship
with account-level resource monitors out of the box (`DAILY_MONITORING`,
`MONTHLY_MONITORING`), so the account-wide safety net exists regardless.
Rather than overwrite that working default with a redundant custom monitor,
this project adds a narrower, **project-scoped** monitor
(`COVID_WH_MONITOR`) on the dedicated `COVID_WH` warehouse — giving early
warning (50%/75% notify) and automatic suspension (90%/100%) specific to
this project's compute, layered on top of Snowflake's own account-level
caps. Confirmed via `SHOW WAREHOUSES LIKE 'COVID_WH';` that the
`resource_monitor` column is set to `COVID_WH_MONITOR`.
