-- Silver: WHO's own situation-report cases/deaths -- an independent
-- cross-check source against JHU_COVID_19 (Task 2 EDA: do WHO and JHU
-- agree on case counts?). Note WHO_SITUATION_REPORTS only covers the
-- period WHO published daily/periodic situation reports (238 distinct
-- report dates total, see sql/03_eda_structure.sql), a shorter window
-- than JHU_COVID_19's full pandemic span -- this is a supplementary
-- cross-check table, not the primary time series.

with source as (
    select * from {{ source('marketplace', 'who_situation_reports') }}
)

select
    iso3166_1                     as iso_code,
    country_region                as country_name,
    date                           as report_date,
    total_cases,
    cases_new,
    deaths,
    deaths_new,
    transmission_classification,
    days_since_last_reported_case
from source
where date is not null
