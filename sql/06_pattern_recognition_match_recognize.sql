-- =====================================================================
-- Task 9: Identify patterns within the COVID dataset using MATCH_RECOGNIZE.
-- Run in Snowsight. Self-contained -- no dependency on Python/dbt.
--
-- Goal: automatically detect "waves" (a sustained rise in new cases
-- followed by a sustained fall) per country, and separately detect
-- short, sharp growth surges -- the kind of pattern that's awkward to
-- express with plain aggregate SQL (it's inherently about the SHAPE of
-- a sequence over time, row-to-row, which is exactly what
-- MATCH_RECOGNIZE is for) but reads almost like plain English once
-- written this way.
-- =====================================================================

USE WAREHOUSE COVID_WH;

-- ---------------------------------------------------------------------
-- Shared prep: daily new confirmed cases per country, smoothed with a
-- 7-day trailing average. Necessary because raw daily deltas are very
-- noisy (weekly reporting cycles cause a sawtooth pattern that would
-- otherwise register as dozens of fake "waves" of length 1) -- smoothing
-- first is what makes wave detection meaningful rather than detecting
-- reporting-cadence artifacts.
-- ---------------------------------------------------------------------
WITH country_daily AS (
    SELECT
        ISO3166_1 AS ISO_CODE,
        COUNTRY_REGION,
        DATE,
        DIFFERENCE AS NEW_CASES
    FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
    WHERE PROVINCE_STATE IS NULL AND COUNTY IS NULL
      AND CASE_TYPE = 'Confirmed'
      AND DATE IS NOT NULL
),
smoothed AS (
    SELECT
        ISO_CODE,
        COUNTRY_REGION,
        DATE,
        AVG(NEW_CASES) OVER (
            PARTITION BY ISO_CODE ORDER BY DATE
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS NEW_CASES_7D_AVG
    FROM country_daily
)

-- ---------------------------------------------------------------------
-- 1) WAVE DETECTION: a sustained rise (5+ consecutive rising days in the
--    smoothed series) followed by a sustained fall (5+ consecutive
--    falling days) = one wave/peak. Requiring 5+ days on each side
--    (rather than 1+) filters out small wobbles and keeps only real
--    waves, given the input is already a 7-day average.
-- ---------------------------------------------------------------------
SELECT *
FROM smoothed
MATCH_RECOGNIZE (
    PARTITION BY ISO_CODE
    ORDER BY DATE
    MEASURES
        FIRST(COUNTRY_REGION)         AS COUNTRY_NAME,
        MATCH_NUMBER()                AS WAVE_NUMBER,
        FIRST(DATE)                   AS WAVE_START,
        LAST(UP.DATE)                 AS PEAK_DATE,
        LAST(DATE)                    AS WAVE_END,
        COUNT(UP.*)                   AS RISING_DAYS,
        COUNT(DOWN.*)                 AS FALLING_DAYS,
        MAX(NEW_CASES_7D_AVG)         AS PEAK_7D_AVG_NEW_CASES
    ONE ROW PER MATCH
    AFTER MATCH SKIP PAST LAST ROW
    PATTERN (UP{5,} DOWN{5,})
    DEFINE
        UP   AS NEW_CASES_7D_AVG > PREV(NEW_CASES_7D_AVG),
        DOWN AS NEW_CASES_7D_AVG <= PREV(NEW_CASES_7D_AVG)
)
ORDER BY ISO_CODE, WAVE_START;

-- ---------------------------------------------------------------------
-- 2) RAPID SURGE DETECTION: a different pattern shape -- 3+ consecutive
--    days where the smoothed series grows by more than 5% day-over-day.
--    Demonstrates DEFINE with an arithmetic condition (not just
--    greater-than comparisons) and a different quantifier. Useful for
--    flagging the *onset* of a wave early, before it's confirmed as a
--    full wave by pattern (1) above.
-- ---------------------------------------------------------------------
WITH country_daily AS (
    SELECT
        ISO3166_1 AS ISO_CODE,
        COUNTRY_REGION,
        DATE,
        DIFFERENCE AS NEW_CASES
    FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
    WHERE PROVINCE_STATE IS NULL AND COUNTY IS NULL
      AND CASE_TYPE = 'Confirmed'
      AND DATE IS NOT NULL
),
smoothed AS (
    SELECT
        ISO_CODE,
        COUNTRY_REGION,
        DATE,
        AVG(NEW_CASES) OVER (
            PARTITION BY ISO_CODE ORDER BY DATE
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS NEW_CASES_7D_AVG
    FROM country_daily
)
SELECT *
FROM smoothed
MATCH_RECOGNIZE (
    PARTITION BY ISO_CODE
    ORDER BY DATE
    MEASURES
        FIRST(COUNTRY_REGION)   AS COUNTRY_NAME,
        MATCH_NUMBER()          AS SURGE_NUMBER,
        FIRST(DATE)             AS SURGE_START,
        LAST(DATE)              AS SURGE_END,
        COUNT(*)                AS SURGE_LENGTH_DAYS,
        FIRST(NEW_CASES_7D_AVG) AS START_LEVEL,
        LAST(NEW_CASES_7D_AVG)  AS END_LEVEL
    ONE ROW PER MATCH
    AFTER MATCH SKIP PAST LAST ROW
    PATTERN (SURGE{3,})
    DEFINE
        SURGE AS NEW_CASES_7D_AVG > 1.05 * PREV(NEW_CASES_7D_AVG)
)
ORDER BY ISO_CODE, SURGE_START;
