-- Silver: country-level mobility only. The source table mixes country
-- totals and sub-national (province/state) rows in one table (see Task 2
-- EDA, sql/03_eda_structure.sql block 7) -- filtering to
-- province_state IS NULL avoids double-counting when this is aggregated
-- downstream.

with source as (
    select * from {{ source('marketplace', 'goog_global_mobility_report') }}
)

select
    country_region                          as country_name,
    date                                     as report_date,
    retail_and_recreation_change_perc       as retail_recreation_change_pct,
    grocery_and_pharmacy_change_perc        as grocery_pharmacy_change_pct,
    parks_change_perc                       as parks_change_pct,
    transit_stations_change_perc            as transit_stations_change_pct,
    workplaces_change_perc                  as workplaces_change_pct,
    residential_change_perc                 as residential_change_pct
from source
where province_state is null
  and date is not null
