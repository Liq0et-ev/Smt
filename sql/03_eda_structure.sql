-- =====================================================================
-- Task 2 (part A): SQL-based structural EDA on the Marketplace dataset.
-- Run in Snowsight against COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.
--
-- Two tiers, per the assignment's literal wording ("analyzing the
-- Snowflake COVID-19 dataset ... to understand its structure, patterns,
-- and gaps" -- the whole dataset, not just the tables we build on):
--   TIER 1 (this file, section 0): a broad landscape survey across ALL
--     44 tables in the Marketplace share -- size, shape, and which ones
--     even have a time dimension. Metadata-only, effectively free to run.
--   TIER 2 (this file, sections 1+, and eda/automated_eda.py): a deep
--     dive on the 4 core tables actually used downstream (JHU_COVID_19,
--     WHO_SITUATION_REPORTS, DATABANK_DEMOGRAPHICS, OWID_VACCINATIONS --
--     Option C / "lean" set, see
--     docs/tasks/task1_marketplace_and_resource_monitors.md for why
--     these four).
-- =====================================================================

USE WAREHOUSE COVID_WH;
USE DATABASE COVID19_EPIDEMIOLOGICAL_DATA;
USE SCHEMA PUBLIC;

-- ---------------------------------------------------------------------
-- 0) TIER 1: broad landscape survey of ALL 44 tables in the share.
--    Pure metadata (INFORMATION_SCHEMA.TABLES.ROW_COUNT/BYTES are
--    maintained by Snowflake, not computed by scanning data), so this
--    costs essentially nothing to run regardless of how large the
--    underlying tables are.
-- ---------------------------------------------------------------------
SELECT
    t.table_name,
    t.row_count,
    ROUND(t.bytes / 1024 / 1024, 1)                    AS size_mb,
    (SELECT COUNT(*) FROM information_schema.columns c
     WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) AS column_count,
    t.comment
FROM information_schema.tables t
WHERE t.table_schema = 'PUBLIC'
ORDER BY t.row_count DESC;

-- Which of the 44 tables even have a date/timestamp column (i.e. are
-- candidates for time-series analysis vs. static reference tables)?
SELECT
    c.table_name,
    LISTAGG(c.column_name, ', ') WITHIN GROUP (ORDER BY c.ordinal_position) AS date_columns
FROM information_schema.columns c
WHERE c.table_schema = 'PUBLIC'
  AND c.data_type IN ('DATE', 'TIMESTAMP_NTZ', 'TIMESTAMP_LTZ', 'TIMESTAMP_TZ')
GROUP BY c.table_name
ORDER BY c.table_name;

-- ---------------------------------------------------------------------
-- 1) JHU_COVID_19: coverage, granularity, and CASE_TYPE breakdown
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                                    AS total_rows,
    COUNT(DISTINCT COUNTRY_REGION)              AS distinct_countries,
    COUNT(DISTINCT CASE_TYPE)                   AS distinct_case_types,
    COUNT_IF(PROVINCE_STATE IS NULL AND COUNTY IS NULL) AS country_level_rows,
    COUNT_IF(PROVINCE_STATE IS NOT NULL OR COUNTY IS NOT NULL) AS sub_national_rows,
    MIN(DATE)                                   AS earliest_date,
    MAX(DATE)                                   AS latest_date
FROM JHU_COVID_19;

-- What CASE_TYPE values actually exist? (staging model assumes 'Confirmed'/'Deaths')
SELECT CASE_TYPE, COUNT(*) AS row_count
FROM JHU_COVID_19
GROUP BY CASE_TYPE
ORDER BY row_count DESC;

-- 2) JHU_COVID_19: data quality -- nulls, negative deltas, duplicate grain
SELECT
    COUNT_IF(CASES IS NULL)      AS null_cases,
    COUNT_IF(DIFFERENCE < 0)     AS negative_difference_rows
FROM JHU_COVID_19
WHERE PROVINCE_STATE IS NULL AND COUNTY IS NULL;

SELECT COUNTRY_REGION, DATE, CASE_TYPE, COUNT(*) AS row_count
FROM JHU_COVID_19
WHERE PROVINCE_STATE IS NULL AND COUNTY IS NULL
GROUP BY COUNTRY_REGION, DATE, CASE_TYPE
HAVING COUNT(*) > 1
ORDER BY row_count DESC
LIMIT 20;

-- 3) JHU_COVID_19: missing-date gaps per country (country-level rows only)
WITH country_level AS (
    SELECT COUNTRY_REGION, DATE
    FROM JHU_COVID_19
    WHERE PROVINCE_STATE IS NULL AND COUNTY IS NULL AND CASE_TYPE = 'Confirmed'
),
country_range AS (
    SELECT COUNTRY_REGION, MIN(DATE) AS start_date, MAX(DATE) AS end_date
    FROM country_level
    GROUP BY COUNTRY_REGION
),
expected_dates AS (
    SELECT
        c.COUNTRY_REGION,
        DATEADD('day', SEQ4(), c.start_date) AS expected_date
    FROM country_range c,
         TABLE(GENERATOR(ROWCOUNT => 5000))
    WHERE DATEADD('day', SEQ4(), c.start_date) <= c.end_date
)
SELECT
    e.COUNTRY_REGION,
    COUNT(*) AS missing_dates
FROM expected_dates e
LEFT JOIN country_level a
    ON a.COUNTRY_REGION = e.COUNTRY_REGION AND a.DATE = e.expected_date
WHERE a.DATE IS NULL
GROUP BY e.COUNTRY_REGION
ORDER BY missing_dates DESC
LIMIT 20;

-- ---------------------------------------------------------------------
-- 4) WHO_SITUATION_REPORTS: coverage window (expected to be shorter than JHU)
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                            AS total_rows,
    COUNT(DISTINCT COUNTRY_REGION)      AS distinct_countries,
    COUNT(DISTINCT DATE)                AS distinct_report_dates,
    MIN(DATE)                           AS earliest_date,
    MAX(DATE)                           AS latest_date
FROM WHO_SITUATION_REPORTS;

-- 5) Cross-check: how much do JHU and WHO agree on overlapping (country, date)?
WITH jhu AS (
    SELECT COUNTRY_REGION, DATE, CASES AS jhu_cases
    FROM JHU_COVID_19
    WHERE PROVINCE_STATE IS NULL AND COUNTY IS NULL AND CASE_TYPE = 'Confirmed'
)
SELECT
    w.COUNTRY_REGION,
    w.DATE,
    w.TOTAL_CASES AS who_cases,
    jhu.jhu_cases,
    jhu.jhu_cases - w.TOTAL_CASES AS diff
FROM WHO_SITUATION_REPORTS w
JOIN jhu ON jhu.COUNTRY_REGION = w.COUNTRY_REGION AND jhu.DATE = w.DATE
WHERE ABS(jhu.jhu_cases - w.TOTAL_CASES) > 1000
ORDER BY ABS(diff) DESC
LIMIT 20;

-- ---------------------------------------------------------------------
-- 6) OWID_VACCINATIONS: coverage
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                                    AS total_rows,
    COUNT(DISTINCT COUNTRY_REGION)              AS distinct_countries,
    MIN(DATE)                                   AS earliest_date,
    MAX(DATE)                                   AS latest_date,
    COUNT_IF(TOTAL_VACCINATIONS IS NULL)        AS null_total_vaccinations
FROM OWID_VACCINATIONS;

-- ---------------------------------------------------------------------
-- 7) DATABANK_DEMOGRAPHICS: confirm global country-level coverage
--    (vs. the similarly-named but US-county-only DEMOGRAPHICS table)
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                        AS total_rows,
    COUNT(DISTINCT COUNTRY_REGION)  AS distinct_countries,
    COUNT_IF(STATE IS NOT NULL)     AS rows_with_state,
    COUNT_IF(TOTAL_POPULATION IS NULL) AS null_population
FROM DATABANK_DEMOGRAPHICS;

-- 8) Coverage check: which countries have cases (JHU) but no demographics row?
SELECT DISTINCT j.COUNTRY_REGION
FROM JHU_COVID_19 j
LEFT JOIN DATABANK_DEMOGRAPHICS d ON d.ISO3166_1 = j.ISO3166_1
WHERE j.PROVINCE_STATE IS NULL AND j.COUNTY IS NULL
  AND d.ISO3166_1 IS NULL
ORDER BY 1;
