-- Silver: global, country-level demographics natively in the Marketplace
-- dataset (confirmed via sample rows: one row per country, e.g.
-- Afghanistan/Albania/Algeria with STATE/COUNTY null -- unlike the
-- similarly-named DEMOGRAPHICS table, which is US-county-only).
-- Population comes from here rather than the external augmentation, so
-- etl/augment_country_indicators.py deliberately does NOT re-fetch
-- population from OWID -- no point duplicating a metric we already have.
--
-- A dbt test against live data (Task 2) found exactly one duplicate
-- iso_code in this source table -- deduped defensively here (keep one
-- row per iso_code, arbitrary but deterministic tiebreak) rather than
-- silently trusting the source is clean.

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
qualify row_number() over (partition by iso3166_1 order by country_region) = 1
