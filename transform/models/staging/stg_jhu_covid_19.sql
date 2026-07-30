-- Silver: JHU_COVID_19 is long-format (one row per country/date/CASE_TYPE,
-- where CASE_TYPE is 'Confirmed' or 'Deaths', CASES is the cumulative
-- count for that type) and mixes country-level rows with sub-national
-- (province/county) rows in the same table. This model:
--   1. filters to country-level only (province_state/county both null),
--      same "avoid double counting" fix as the mobility table needed;
--   2. excludes rows with no ISO 3166-1 code -- JHU tracks some entries
--      (e.g. cruise ships like "Diamond Princess"/"MS Zaandam", or
--      Olympics-related rows) that aren't real countries and have no
--      code; discovered via a dbt test failure on real data (Task 2)
--      showing duplicate/null (iso_code, date) combinations;
--   3. aggregates country_name with MAX() rather than GROUP BY-ing on it
--      directly, so a country appearing under slightly different name
--      spellings on the same date (also found via the same test
--      failure) still collapses into one row per (iso_code, date)
--      instead of one row per (iso_code, name, date);
--   4. pivots CASE_TYPE into columns via conditional aggregation, giving
--      one row per (country, date) with confirmed_cases/confirmed_deaths
--      side by side -- much easier to work with downstream.

with source as (
    select * from {{ source('marketplace', 'jhu_covid_19') }}
)

select
    iso3166_1                                              as iso_code,
    max(country_region)                                     as country_name,
    date                                                     as report_date,
    max(case when case_type = 'Confirmed' then cases end)   as confirmed_cases,
    max(case when case_type = 'Deaths' then cases end)      as confirmed_deaths
from source
where province_state is null
  and county is null
  and date is not null
  and iso3166_1 is not null
group by iso3166_1, date
