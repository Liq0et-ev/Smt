-- Silver: cleaned/renamed ECDC cases+deaths, one row per (country, date).
-- Source-conformed naming (snake_case, unambiguous names) so downstream
-- marts don't need to know the Marketplace table's original column names.

with source as (
    select * from {{ source('marketplace', 'ecdc_global') }}
)

select
    country_region as country_name,
    date            as report_date,
    cases           as confirmed_cases,
    deaths          as confirmed_deaths
from source
where date is not null
