-- =====================================================================
-- Task 1 (part C): Resource Monitors
-- Run as ACCOUNTADMIN.
-- Purpose: protect the free trial's credit balance for the duration of
-- the capstone (4 days) by capping both account-wide and warehouse-level
-- spend, with early-warning notifications before anything is suspended.
-- =====================================================================

USE ROLE ACCOUNTADMIN;

-- ---------------------------------------------------------------------
-- 1) Warehouse-level monitor: caps daily spend of COVID_WH specifically.
--    A trial account starts with $400 in credits; XS warehouses burn
--    ~1 credit/hour while running, so 5 credits/day is generous headroom
--    for interactive work while still catching a runaway query/loop.
-- ---------------------------------------------------------------------
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

-- ---------------------------------------------------------------------
-- 2) Account-level monitor: safety net across ALL warehouses in the
--    account (in case other default warehouses, e.g. COMPUTE_WH, get
--    used too). Quota set conservatively relative to the trial balance.
-- ---------------------------------------------------------------------
CREATE RESOURCE MONITOR IF NOT EXISTS ACCOUNT_MONITOR
    WITH
        CREDIT_QUOTA = 25
        FREQUENCY    = MONTHLY
        START_TIMESTAMP = IMMEDIATELY
        TRIGGERS
            ON 50  PERCENT DO NOTIFY
            ON 75  PERCENT DO NOTIFY
            ON 90  PERCENT DO SUSPEND
            ON 100 PERCENT DO SUSPEND_IMMEDIATE;

ALTER ACCOUNT SET RESOURCE_MONITOR = ACCOUNT_MONITOR;

-- ---------------------------------------------------------------------
-- 3) Make sure your user receives the NOTIFY triggers (Snowsight shows
--    these as in-app notifications automatically for ACCOUNTADMIN /
--    users granted MONITOR on the resource monitor; no extra config
--    needed for in-app alerts on a trial account).
-- ---------------------------------------------------------------------

-- Verification
SHOW RESOURCE MONITORS;
SHOW WAREHOUSES LIKE 'COVID_WH';
