-- =====================================================================
-- Task 1 (part A): Project compute + working database setup
-- Run as ACCOUNTADMIN (or a role with CREATE WAREHOUSE / CREATE DATABASE)
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
-- database — see 01_get_marketplace_dataset.md — we do NOT create that one.)
CREATE DATABASE IF NOT EXISTS COVID19_PLATFORM
    COMMENT = 'Working database for the COVID-19 Data Integration, Analysis, and Visualization Platform capstone';

CREATE SCHEMA IF NOT EXISTS COVID19_PLATFORM.RAW;         -- landing zone for external augmentation data (Kaggle demographics/economics)
CREATE SCHEMA IF NOT EXISTS COVID19_PLATFORM.ANALYTICS;   -- curated/enriched tables & views used by the API
CREATE SCHEMA IF NOT EXISTS COVID19_PLATFORM.ML;          -- forecasting / clustering output tables

USE WAREHOUSE COVID_WH;
USE DATABASE COVID19_PLATFORM;

-- Sanity check
SELECT CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_WAREHOUSE(), CURRENT_DATABASE();
