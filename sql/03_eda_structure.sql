-- =====================================================================
-- Task 2 (part A): SQL-based structural EDA on the Marketplace dataset.
-- Run in Snowsight against COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.
-- Goal: understand structure, patterns, and gaps in the core tables
-- before we augment/model on top of them.
-- =====================================================================

USE WAREHOUSE COVID_WH;
USE DATABASE COVID19_EPIDEMIOLOGICAL_DATA;
USE SCHEMA PUBLIC;

-- ---------------------------------------------------------------------
-- 0) JHU_COVID_19: schema not yet confirmed against the live account.
--    Run this first and share the output before relying on the table
--    below it -- other queries in this file assume the confirmed
--    schemas already captured in docs/tasks/task1_marketplace_and_resource_monitors.md
--    (ECDC_GLOBAL, OWID_VACCINATIONS, GOOG_GLOBAL_MOBILITY_REPORT, APPLE_MOBILITY).
-- ---------------------------------------------------------------------
DESCRIBE TABLE JHU_COVID_19;
SELECT * FROM JHU_COVID_19 LIMIT 20;

-- ---------------------------------------------------------------------
-- 1) ECDC_GLOBAL: coverage and date range
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                           AS total_rows,
    COUNT(DISTINCT COUNTRY_REGION)     AS distinct_countries,
    MIN(DATE)                          AS earliest_date,
    MAX(DATE)                          AS latest_date,
    DATEDIFF('day', MIN(DATE), MAX(DATE)) AS days_span
FROM ECDC_GLOBAL;

-- 2) ECDC_GLOBAL: data quality -- nulls and negative values (reporting
--    corrections in COVID data often show up as negative daily deltas)
SELECT
    COUNT_IF(CASES IS NULL)   AS null_cases,
    COUNT_IF(DEATHS IS NULL)  AS null_deaths,
    COUNT_IF(CASES < 0)       AS negative_case_rows,
    COUNT_IF(DEATHS < 0)      AS negative_death_rows
FROM ECDC_GLOBAL;

-- 3) ECDC_GLOBAL: duplicate (country, date) pairs -- should be zero if
--    the table is a clean daily grain; non-zero reveals a data quality gap
SELECT COUNTRY_REGION, DATE, COUNT(*) AS row_count
FROM ECDC_GLOBAL
GROUP BY COUNTRY_REGION, DATE
HAVING COUNT(*) > 1
ORDER BY row_count DESC
LIMIT 20;

-- 4) ECDC_GLOBAL: which countries have reporting gaps (missing dates in
--    their own min/max range)? Uses a generated calendar spine per country.
WITH country_range AS (
    SELECT COUNTRY_REGION, MIN(DATE) AS start_date, MAX(DATE) AS end_date
    FROM ECDC_GLOBAL
    GROUP BY COUNTRY_REGION
),
expected_dates AS (
    SELECT
        c.COUNTRY_REGION,
        DATEADD('day', SEQ4(), c.start_date) AS expected_date
    FROM country_range c,
         TABLE(GENERATOR(ROWCOUNT => 5000)) -- upper bound on days spanned
    WHERE DATEADD('day', SEQ4(), c.start_date) <= c.end_date
)
SELECT
    e.COUNTRY_REGION,
    COUNT(*) AS missing_dates
FROM expected_dates e
LEFT JOIN ECDC_GLOBAL a
    ON a.COUNTRY_REGION = e.COUNTRY_REGION AND a.DATE = e.expected_date
WHERE a.DATE IS NULL
GROUP BY e.COUNTRY_REGION
ORDER BY missing_dates DESC
LIMIT 20;

-- ---------------------------------------------------------------------
-- 5) OWID_VACCINATIONS: coverage and structural gaps
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                                    AS total_rows,
    COUNT(DISTINCT COUNTRY_REGION)              AS distinct_countries,
    MIN(DATE)                                   AS earliest_date,
    MAX(DATE)                                   AS latest_date,
    COUNT_IF(TOTAL_VACCINATIONS IS NULL)        AS null_total_vaccinations,
    COUNT_IF(PEOPLE_FULLY_VACCINATED IS NULL)   AS null_fully_vaccinated
FROM OWID_VACCINATIONS;

-- 6) Cross-check: which countries appear in ECDC_GLOBAL (cases/deaths)
--    but never appear in OWID_VACCINATIONS (vaccination gap)?
SELECT DISTINCT e.COUNTRY_REGION
FROM ECDC_GLOBAL e
LEFT JOIN OWID_VACCINATIONS v ON v.COUNTRY_REGION = e.COUNTRY_REGION
WHERE v.COUNTRY_REGION IS NULL
ORDER BY 1;

-- ---------------------------------------------------------------------
-- 7) GOOG_GLOBAL_MOBILITY_REPORT: this is the largest table (11.7M rows)
--    -- confirm granularity (country-level vs sub-region) before using it
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                                        AS total_rows,
    COUNT(DISTINCT COUNTRY_REGION)                  AS distinct_countries,
    COUNT_IF(PROVINCE_STATE IS NULL)                AS country_level_rows,
    COUNT_IF(PROVINCE_STATE IS NOT NULL)             AS sub_national_rows,
    MIN(DATE)                                       AS earliest_date,
    MAX(DATE)                                       AS latest_date
FROM GOOG_GLOBAL_MOBILITY_REPORT;

-- ---------------------------------------------------------------------
-- 8) DEMOGRAPHICS: confirm it really is US-county-only (Task 1 finding)
--    -- this is the justification for the Task 2 Python augmentation step
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                        AS total_rows,
    COUNT(DISTINCT STATE)           AS distinct_states,
    COUNT(DISTINCT ISO3166_1)       AS distinct_country_codes
FROM DEMOGRAPHICS;
