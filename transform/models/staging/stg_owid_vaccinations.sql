-- Silver: cleaned/renamed vaccination rollout, one row per (iso_code, date).
--
-- Same issue as stg_jhu_covid_19 (Task 2 live-data testing): grouping by
-- (iso_code, country_name, date) instead of just (iso_code, date) let
-- name-spelling variants for the same country produce duplicate rows,
-- which then fanned out the LEFT JOIN in the Gold mart
-- (country_daily_enriched joins on iso_code + report_date). Aggregating
-- here instead of just selecting avoids that.

with source as (
    select * from {{ source('marketplace', 'owid_vaccinations') }}
)

select
    iso3166_1                                  as iso_code,
    max(country_region)                         as country_name,
    date                                         as report_date,
    max(total_vaccinations)                     as total_vaccinations,
    max(people_vaccinated)                      as people_vaccinated,
    max(people_fully_vaccinated)                as people_fully_vaccinated,
    max(daily_vaccinations)                     as daily_vaccinations,
    max(total_vaccinations_per_hundred)         as total_vaccinations_per_hundred,
    max(people_vaccinated_per_hundred)          as people_vaccinated_per_hundred,
    max(people_fully_vaccinated_per_hundred)    as people_fully_vaccinated_per_hundred
from source
where date is not null
  and iso3166_1 is not null
group by iso3166_1, date
