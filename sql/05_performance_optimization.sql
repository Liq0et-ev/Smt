-- =====================================================================
-- Task 7: Performance Optimization
-- Run in Snowsight. Self-contained -- does NOT depend on dbt having run
-- (the Python connector issue tracked in Task 2 doesn't block this file
-- at all; everything here is plain SQL against tables you already have
-- access to).
--
-- Why this can't optimize the Marketplace tables directly: the
-- Marketplace share (COVID19_EPIDEMIOLOGICAL_DATA) is READ-ONLY --
-- Starschema owns it, we only have IMPORTED PRIVILEGES. We can't add a
-- clustering key, a materialized view, or search optimization to a
-- table we don't own. So the optimization story here is: build a
-- *smaller, purpose-shaped copy* of the data we actually query
-- (matching what the dbt Gold layer will eventually be), and optimize
-- THAT -- which is the realistic pattern in any data warehouse anyway
-- (you don't get to tune someone else's shared source tables).
-- =====================================================================

USE WAREHOUSE COVID_WH;
USE DATABASE COVID19_PLATFORM;

-- ---------------------------------------------------------------------
-- 0) BASELINE: profile a query against the raw, un-clustered Marketplace
--    table (9.7M rows) -- note the bytes/partitions scanned here, then
--    compare against section 2 below. Open this query's "Query Profile"
--    in Snowsight (History -> click the query -> Profile tab) to see
--    the actual partition-pruning statistics.
-- ---------------------------------------------------------------------
SELECT COUNTRY_REGION, ISO3166_1, DATE,
       MAX(CASE WHEN CASE_TYPE = 'Confirmed' THEN CASES END) AS confirmed_cases,
       MAX(CASE WHEN CASE_TYPE = 'Deaths' THEN CASES END)    AS confirmed_deaths
FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
WHERE PROVINCE_STATE IS NULL AND COUNTY IS NULL
  AND ISO3166_1 = 'US'
GROUP BY COUNTRY_REGION, ISO3166_1, DATE
ORDER BY DATE;

-- ---------------------------------------------------------------------
-- 1) Build our own copy of the pivoted, country-level data -- this is
--    the same transformation as transform/models/staging/stg_jhu_covid_19.sql,
--    done here in plain SQL so it doesn't depend on dbt/Python having run.
--    (Once the Python connector issue is resolved, `dbt run` will build
--    and maintain the real version of this table -- this manual version
--    is a stand-in so Task 7 isn't blocked by Task 2's open issue.)
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE GOLD.JHU_COUNTRY_DAILY AS
SELECT
    ISO3166_1     AS ISO_CODE,
    COUNTRY_REGION AS COUNTRY_NAME,
    DATE           AS REPORT_DATE,
    MAX(CASE WHEN CASE_TYPE = 'Confirmed' THEN CASES END) AS CONFIRMED_CASES,
    MAX(CASE WHEN CASE_TYPE = 'Deaths' THEN CASES END)    AS CONFIRMED_DEATHS
FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
WHERE PROVINCE_STATE IS NULL AND COUNTY IS NULL AND DATE IS NOT NULL
GROUP BY ISO3166_1, COUNTRY_REGION, DATE;

-- ---------------------------------------------------------------------
-- 2) CLUSTERING KEY: the table above is naturally loaded in JHU's
--    original order (roughly alphabetical by country, chronological
--    within country from the source), which happens to already cluster
--    reasonably well by (ISO_CODE, REPORT_DATE) -- exactly the columns
--    the API (Task 4) will filter/sort by ("give me country X between
--    date A and B"). An explicit clustering key tells Snowflake to
--    actively maintain that physical ordering as the table changes,
--    so micro-partition pruning stays effective instead of degrading
--    over time as new data is loaded out of order.
-- ---------------------------------------------------------------------
ALTER TABLE GOLD.JHU_COUNTRY_DAILY CLUSTER BY (ISO_CODE, REPORT_DATE);

-- Check clustering quality (average_depth close to 1 = well-clustered;
-- higher = more overlapping micro-partitions = less pruning benefit)
SELECT SYSTEM$CLUSTERING_INFORMATION('GOLD.JHU_COUNTRY_DAILY', '(ISO_CODE, REPORT_DATE)');

-- ---------------------------------------------------------------------
-- 3) COMPARE: the same "one country's full time series" query, now
--    against the clustered, pre-pivoted table. Compare this query's
--    Profile (bytes scanned, partitions scanned) against section 0 --
--    should scan dramatically fewer partitions since CASE_TYPE
--    pivoting/filtering is already done and the data is clustered by
--    exactly what we're filtering on.
-- ---------------------------------------------------------------------
SELECT * FROM GOLD.JHU_COUNTRY_DAILY
WHERE ISO_CODE = 'US'
ORDER BY REPORT_DATE;

-- ---------------------------------------------------------------------
-- 4) MATERIALIZED VIEW: a dashboard's "global daily totals" chart
--    (Task 5) re-aggregates the same GROUP BY on every page load if
--    left as a plain view. A materialized view pre-computes and
--    incrementally maintains the result, so repeated reads are close
--    to instant instead of re-scanning/re-aggregating every time.
--    (Snowflake materialized views only support a single source table
--    with no joins -- fits this case exactly.)
-- ---------------------------------------------------------------------
CREATE OR REPLACE MATERIALIZED VIEW GOLD.GLOBAL_DAILY_SUMMARY AS
SELECT
    REPORT_DATE,
    SUM(CONFIRMED_CASES)  AS GLOBAL_CASES,
    SUM(CONFIRMED_DEATHS) AS GLOBAL_DEATHS
FROM GOLD.JHU_COUNTRY_DAILY
GROUP BY REPORT_DATE;

-- Repeated reads of this are served from the maintained MV, not
-- recomputed from the base table each time:
SELECT * FROM GOLD.GLOBAL_DAILY_SUMMARY ORDER BY REPORT_DATE DESC LIMIT 30;

-- ---------------------------------------------------------------------
-- 5) Other Snowflake performance features in play, already covered
--    elsewhere or not code-demonstrable on a trial account:
--    - Result caching: Snowflake automatically caches a query's results
--      for 24h if neither the query nor the underlying data changed --
--      no code needed, it's automatic and applies to every query above
--      on a re-run.
--    - Warehouse right-sizing: COVID_WH is XSMALL with 60s auto-suspend
--      (sql/00_setup_warehouse_and_db.sql, Task 1) -- avoids paying for
--      idle/oversized compute, the most common real-world "performance"
--      mistake being cost, not speed.
--    - Search Optimization Service: worth mentioning for point-lookup-
--      heavy workloads (e.g. searching MongoDB-style across many
--      non-clustered columns), but adds ongoing credit cost -- not
--      enabled here given this is a trial account with a tight
--      resource-monitor budget (Task 1); documented as a known lever
--      rather than turned on speculatively.
-- ---------------------------------------------------------------------
