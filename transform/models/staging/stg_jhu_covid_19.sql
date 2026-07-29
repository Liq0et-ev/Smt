-- Silver: JHU_COVID_19 is long-format (one row per country/date/CASE_TYPE,
-- where CASE_TYPE is 'Confirmed' or 'Deaths', CASES is the cumulative
-- count for that type) and mixes country-level rows with sub-national
-- (province/county) rows in the same table. This model:
--   1. filters to country-level only (province_state/county both null),
--      same "avoid double counting" fix as the mobility table needed;
--   2. pivots CASE_TYPE into columns via conditional aggregation, giving
--      one row per (country, date) with confirmed_cases/confirmed_deaths
--      side by side -- much easier to work with downstream.

with source as (
    select * from {{ source('marketplace', 'jhu_covid_19') }}
)

select
    iso3166_1                                              as iso_code,
    country_region                                          as country_name,
    date                                                     as report_date,
    max(case when case_type = 'Confirmed' then cases end)   as confirmed_cases,
    max(case when case_type = 'Deaths' then cases end)      as confirmed_deaths
from source
where province_state is null
  and county is null
  and date is not null
group by iso3166_1, country_region, date
