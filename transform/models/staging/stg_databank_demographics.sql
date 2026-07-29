-- Silver: global, country-level demographics natively in the Marketplace
-- dataset (confirmed via sample rows: one row per country, e.g.
-- Afghanistan/Albania/Algeria with STATE/COUNTY null -- unlike the
-- similarly-named DEMOGRAPHICS table, which is US-county-only).
-- Population comes from here rather than the external augmentation, so
-- etl/augment_country_indicators.py deliberately does NOT re-fetch
-- population from OWID -- no point duplicating a metric we already have.

with source as (
    select * from {{ source('marketplace', 'databank_demographics') }}
)

select
    iso3166_1                  as iso_code,
    country_region              as country_name,
    total_population,
    total_male_population,
    total_female_population
from source
where iso3166_1 is not null
