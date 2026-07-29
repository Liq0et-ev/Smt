-- Silver: cleaned country-level demographic/economic indicators
-- (Bronze -> Silver step of the augmentation pipeline).

with source as (
    select * from {{ source('bronze', 'country_indicators') }}
)

select
    iso_code,
    continent,
    location                     as country_name,
    population,
    population_density,
    median_age,
    gdp_per_capita,
    hospital_beds_per_thousand,
    human_development_index,
    life_expectancy,
    diabetes_prevalence,
    extreme_poverty
from source
where iso_code is not null
