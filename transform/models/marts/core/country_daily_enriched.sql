-- Gold: the main API/dashboard-facing mart. One row per (country, date)
-- with cases/deaths, vaccination progress, and demographic/economic
-- context joined together, plus derived population-adjusted metrics.
--
-- All joins are on ISO 3166-1 country code, not country name -- every
-- Option C source table carries iso_code natively 
with cases as (
    select * from {{ ref('stg_jhu_covid_19') }}
),

vaccinations as (
    select * from {{ ref('stg_owid_vaccinations') }}
),

demographics as (
    select * from {{ ref('stg_databank_demographics') }}
),

indicators as (
    select * from {{ ref('stg_country_indicators') }}
),

joined as (
    select
        cases.iso_code,
        cases.country_name,
        cases.report_date,
        cases.confirmed_cases,
        cases.confirmed_deaths,

        vaccinations.total_vaccinations,
        vaccinations.people_fully_vaccinated,
        vaccinations.people_fully_vaccinated_per_hundred,

        demographics.total_population,
        demographics.total_male_population,
        demographics.total_female_population,

        indicators.continent,
        indicators.median_age,
        indicators.gdp_per_capita,
        indicators.hospital_beds_per_thousand,
        indicators.human_development_index

    from cases
    left join vaccinations
        on cases.iso_code = vaccinations.iso_code
        and cases.report_date = vaccinations.report_date
    left join demographics
        on cases.iso_code = demographics.iso_code
    left join indicators
        on cases.iso_code = indicators.iso_code
)

select
    *,
    case when total_population > 0
         then confirmed_cases / total_population * 100000
         else null end as cases_per_100k,
    case when total_population > 0
         then confirmed_deaths / total_population * 100000
         else null end as deaths_per_100k,
    case when confirmed_cases > 0
         then confirmed_deaths / confirmed_cases
         else null end as case_fatality_rate
from joined
