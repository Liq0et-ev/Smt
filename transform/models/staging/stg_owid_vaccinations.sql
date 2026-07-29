-- Silver: cleaned/renamed vaccination rollout, one row per (country, date).

with source as (
    select * from {{ source('marketplace', 'owid_vaccinations') }}
)

select
    country_region                          as country_name,
    iso3166_1                               as iso_code,
    date                                     as report_date,
    total_vaccinations,
    people_vaccinated,
    people_fully_vaccinated,
    daily_vaccinations,
    total_vaccinations_per_hundred,
    people_vaccinated_per_hundred,
    people_fully_vaccinated_per_hundred
from source
where date is not null
