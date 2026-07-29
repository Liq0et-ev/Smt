-- =====================================================================
-- Task 1 (part A): Project compute + working database setup
-- Run as ACCOUNTADMIN (or a role with CREATE WAREHOUSE / CREATE DATABASE)
--
-- Storage layer follows Medallion Architecture (Bronze / Silver / Gold),
-- the same pattern taught in the bootcamp's Databricks/Delta Lake module
-- -- here implemented on Snowflake instead of Delta Lake, transformed
-- bronze->silver->gold with dbt (see transform/).
-- =====================================================================

-- Dedicated, small, auto-suspending warehouse so the trial account
-- doesn't burn credits when nobody is querying.
CREATE WAREHOUSE IF NOT EXISTS COVID_WH
    WAREHOUSE_SIZE      = 'XSMALL'
    AUTO_SUSPEND         = 60          -- seconds of idle time before suspend
    AUTO_RESUME          = TRUE
    INITIALLY_SUSPENDED  = TRUE
    COMMENT              = 'Compute for COVID-19 Data Platform project';

-- Working database for our own tables: augmented/enriched data,
-- EDA outputs, forecasting results, clustering results, materialized views.
-- (The Marketplace dataset itself arrives as its OWN read-only shared
-- database -- see docs/tasks/task1_marketplace_and_resource_monitors.md --
-- we do NOT create that one, only reference it as a dbt source.)
CREATE DATABASE IF NOT EXISTS COVID19_PLATFORM
    COMMENT = 'Working database for the COVID-19 Data Integration, Analysis, and Visualization Platform capstone';

-- Drop the earlier RAW/ANALYTICS/ML schema names (pre-Medallion-rename;
-- these were never loaded with data, so dropping is safe) and replace
-- with the three Medallion layers.
DROP SCHEMA IF EXISTS COVID19_PLATFORM.RAW;
DROP SCHEMA IF EXISTS COVID19_PLATFORM.ANALYTICS;
DROP SCHEMA IF EXISTS COVID19_PLATFORM.ML;

-- BRONZE: landing zone for external data we ingest ourselves with Python
-- (e.g. Our World in Data country indicators) -- as-fetched, unmodified.
CREATE SCHEMA IF NOT EXISTS COVID19_PLATFORM.BRONZE
    COMMENT = 'Medallion Bronze layer: raw external data, as ingested';

-- SILVER: cleaned, deduplicated, joined tables built by dbt staging/
-- intermediate models from Bronze + the Marketplace source tables.
CREATE SCHEMA IF NOT EXISTS COVID19_PLATFORM.SILVER
    COMMENT = 'Medallion Silver layer: cleaned/conformed/joined tables (dbt staging+intermediate models)';

-- GOLD: business-level marts -- API-serving aggregates, forecasting
-- output, clustering output. What the FastAPI backend and dashboard
-- actually query.
CREATE SCHEMA IF NOT EXISTS COVID19_PLATFORM.GOLD
    COMMENT = 'Medallion Gold layer: consumption-ready marts (dbt mart models) + ML outputs';

USE WAREHOUSE COVID_WH;
USE DATABASE COVID19_PLATFORM;

-- Sanity check
SELECT CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_WAREHOUSE(), CURRENT_DATABASE();
SHOW SCHEMAS IN DATABASE COVID19_PLATFORM;
