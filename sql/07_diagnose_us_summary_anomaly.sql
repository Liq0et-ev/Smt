-- Diagnostic for the /countries/US/summary anomaly found while testing the
-- API live: it returned latest_date = 2020-03-24 with confirmed_cases = 0,
-- instead of a recent date with a large cumulative count.
--
-- This is NOT about the ISO code bug (fixed separately in
-- etl/augment_country_indicators.py) -- this checks a different, real
-- possibility: JHU/CSSE is documented to have switched the US from a single
-- country-level row to per-state/county reporting partway through March
-- 2020. If true, the country-level "US" row (PROVINCE_STATE and COUNTY
-- both NULL) our staging model filters to may simply stop existing after
-- that date -- meaning stg_jhu_covid_19 has no real "latest" US row, and
-- the Gold mart is correctly reporting the last one that exists.
--
-- Run each block and check the results.

-- 1. Does a country-level ("PROVINCE_STATE"/"COUNTY" both NULL) 'US' row
--    exist for CASE_TYPE = 'Confirmed' beyond March 2020?
SELECT
    MIN(DATE) AS first_date,
    MAX(DATE) AS last_date,
    COUNT(*)  AS row_count
FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
WHERE ISO3166_1 = 'US'
  AND PROVINCE_STATE IS NULL
  AND COUNTY IS NULL
  AND CASE_TYPE = 'Confirmed';

-- 2. If (1) shows a short/early date range, where does the US data
--    actually live after that date? (state-level rows, still under 'US')
SELECT
    MIN(DATE) AS first_date,
    MAX(DATE) AS last_date,
    COUNT(DISTINCT PROVINCE_STATE) AS distinct_states,
    COUNT(*) AS row_count
FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
WHERE ISO3166_1 = 'US'
  AND PROVINCE_STATE IS NOT NULL
  AND COUNTY IS NULL
  AND CASE_TYPE = 'Confirmed';

-- 3. Sanity check: does the same pattern (country row stops early) show up
--    for OTHER countries, or is it US-specific? Pick a couple of others.
SELECT
    ISO3166_1,
    MIN(DATE) AS first_date,
    MAX(DATE) AS last_date,
    COUNT(*)  AS row_count
FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
WHERE ISO3166_1 IN ('DE', 'FR', 'IN', 'BR')
  AND PROVINCE_STATE IS NULL
  AND COUNTY IS NULL
  AND CASE_TYPE = 'Confirmed'
GROUP BY ISO3166_1
ORDER BY ISO3166_1;
