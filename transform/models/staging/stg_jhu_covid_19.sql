-- Silver: JHU_COVID_19 is long-format (one row per country/date/CASE_TYPE,
-- where CASE_TYPE is 'Confirmed' or 'Deaths', CASES is the cumulative
-- count for that type) and mixes country-level rows with sub-national
-- (province/county) rows in the same table. This model:
--   1. prefers the country-level row (province_state/county both null)
--      for a given (iso_code, date), but falls back to summing
--      state-level rows (province_state populated, county null) for
--      dates where no country-level row exists. Discovered via live-data
--      diagnosis (sql/07_diagnose_us_summary_anomaly.sql) that several
--      countries -- the US most severely -- have only a handful of
--      country-level rows before the source switches to state-level
--      granularity for them; without the fallback, those countries'
--      Gold-layer history effectively ends within months of the
--      pandemic's start;
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
),

country_level as (
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
),

state_level_summed as (
    select
        iso3166_1                                              as iso_code,
        max(country_region)                                     as country_name,
        date                                                     as report_date,
        sum(case when case_type = 'Confirmed' then cases end)   as confirmed_cases,
        sum(case when case_type = 'Deaths' then cases end)      as confirmed_deaths
    from source
    where province_state is not null
      and county is null
      and date is not null
      and iso3166_1 is not null
    group by iso3166_1, date
)

select
    coalesce(country_level.iso_code, state_level_summed.iso_code)             as iso_code,
    coalesce(country_level.country_name, state_level_summed.country_name)     as country_name,
    coalesce(country_level.report_date, state_level_summed.report_date)       as report_date,
    coalesce(country_level.confirmed_cases, state_level_summed.confirmed_cases)   as confirmed_cases,
    coalesce(country_level.confirmed_deaths, state_level_summed.confirmed_deaths) as confirmed_deaths
from country_level
full outer join state_level_summed
    on country_level.iso_code = state_level_summed.iso_code
    and country_level.report_date = state_level_summed.report_date
