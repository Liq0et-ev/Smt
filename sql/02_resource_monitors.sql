-- =====================================================================
-- Task 1 (part C): Resource Monitors
-- Run as ACCOUNTADMIN.
-- Purpose: protect the free trial's credit balance for the duration of
-- the capstone (4 days) by capping this project's compute spend, with
-- early-warning notifications before anything is suspended.
--
-- NOTE: Snowflake trial accounts already ship with two built-in,
-- account-level resource monitors (verified via SHOW RESOURCE MONITORS
-- on this account): DAILY_MONITORING (30 credit/day) and
-- MONTHLY_MONITORING (380 credit/month, attached at ACCOUNT level).
-- Replacing the account-level monitor with a custom one would remove
-- that existing safety net for no real benefit, so this script only
-- adds a project-scoped warehouse monitor on top of it.
-- =====================================================================

USE ROLE ACCOUNTADMIN;

-- Warehouse-level monitor: caps daily spend of COVID_WH specifically.
-- A trial account starts with $400 in credits; XS warehouses burn
-- ~1 credit/hour while running, so 5 credits/day is generous headroom
-- for interactive work while still catching a runaway query/loop,
-- independent of (and in addition to) the account-wide defaults above.
CREATE RESOURCE MONITOR IF NOT EXISTS COVID_WH_MONITOR
    WITH
        CREDIT_QUOTA = 5
        FREQUENCY    = DAILY
        START_TIMESTAMP = IMMEDIATELY
        TRIGGERS
            ON 50  PERCENT DO NOTIFY
            ON 75  PERCENT DO NOTIFY
            ON 90  PERCENT DO SUSPEND
            ON 100 PERCENT DO SUSPEND_IMMEDIATE;

ALTER WAREHOUSE COVID_WH SET RESOURCE_MONITOR = COVID_WH_MONITOR;

-- Verification
SHOW RESOURCE MONITORS;
SHOW WAREHOUSES LIKE 'COVID_WH';
