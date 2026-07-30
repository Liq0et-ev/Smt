/* Investigates the /countries/US/summary issue found during live API testing.
The endpoint returned latest_date = 2020-03-24 with confirmed_cases = 0
instead of recent cumulative data.

This is NOT related to the ISO code bug (fixed separately in etl/augment_country_indicators.py). 
Instead, it checks whether JHU/CSSE stopped publishing a country-level US record after switching to
state/county reporting in March 2020.

If the country-level "US" row (PROVINCE_STATE and COUNTY are NULL) no
longer exists after that date, then stg_jhu_covid_19 has no newer US row,
and the Gold mart is correctly returning the last available one.
*/

/*1.Check whether a country-level 'US' row
(PROVINCE_STATE and COUNTY are both NULL)
exists for CASE_TYPE = 'Confirmed' after March 2020.
*/
SELECT
    MIN(DATE) AS first_date,
    MAX(DATE) AS last_date,
    COUNT(*)  AS row_count
FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
WHERE ISO3166_1 = 'US'
  AND PROVINCE_STATE IS NULL
  AND COUNTY IS NULL
  AND CASE_TYPE = 'Confirmed';

/*2.If not, check where the US data is stored after March 2020
(e.g., state-level rows under 'US').
*/
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

/*3. Verify whether the same behavior (country-level rows ending early)
occurs for other countries, or if it is specific to the US.
Test with a few example countries.
*/

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

/*4. Both the "sum by date" and "sum of each state's own max" reconstructions
for the US topped out in the low hundreds of thousands, nowhere near
the real 103 million total -- meaning CASES probably doesn't mean
what we assumed at state level. Look at the raw rows for one well-known
state (California) to see what's actually in there.
*/
SELECT DATE, PROVINCE_STATE, CASE_TYPE, CASES, DIFFERENCE
FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
WHERE ISO3166_1 = 'US'
  AND PROVINCE_STATE = 'California'
  AND COUNTY IS NULL
ORDER BY DATE DESC
LIMIT 30;

/*5. Find the maximum CASES value ever recorded for California to determine
the highest value this column reached and understand what it represents. 
*/

SELECT CASE_TYPE, MAX(CASES) AS MAX_CASES, COUNT(*) AS ROW_COUNT
FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
WHERE ISO3166_1 = 'US'
  AND PROVINCE_STATE = 'California'
  AND COUNTY IS NULL
GROUP BY CASE_TYPE;
