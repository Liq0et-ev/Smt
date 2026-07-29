-- Gold: the main API/dashboard-facing mart. One row per (country, date)
-- with cases/deaths, vaccination progress, mobility, and demographic/
-- economic context all joined together, plus derived population-adjusted
-- metrics.
--
-- KNOWN LIMITATION: joins are on country NAME (no common ISO code is
-- confirmed across all four sources yet -- OWID_VACCINATIONS has
-- iso3166_1, but ECDC_GLOBAL's ISO column wasn't in the confirmed
-- schema as of this commit). Country-name spelling can differ across
-- sources (e.g. "United States" vs "US"). Task 2 EDA should compare
-- distinct country name lists across sources and this model should
-- move to an ISO-code join (with a small manual crosswalk for
-- mismatches) once that's done -- tracked as a follow-up, not silently
-- ignored.

with cases as (
    select * from {{ ref('stg_ecdc_global') }}
),

vaccinations as (
    select * from {{ ref('stg_owid_vaccinations') }}
),

mobility as (
    select * from {{ ref('stg_google_mobility') }}
),

indicators as (
    select * from {{ ref('stg_country_indicators') }}
),

joined as (
    select
        cases.country_name,
        cases.report_date,
        cases.confirmed_cases,
        cases.confirmed_deaths,

        vaccinations.total_vaccinations,
        vaccinations.people_fully_vaccinated,
        vaccinations.people_fully_vaccinated_per_hundred,

        mobility.retail_recreation_change_pct,
        mobility.workplaces_change_pct,
        mobility.residential_change_pct,

        indicators.iso_code,
        indicators.continent,
        indicators.population,
        indicators.median_age,
        indicators.gdp_per_capita,
        indicators.hospital_beds_per_thousand,
        indicators.human_development_index

    from cases
    left join vaccinations
        on lower(cases.country_name) = lower(vaccinations.country_name)
        and cases.report_date = vaccinations.report_date
    left join mobility
        on lower(cases.country_name) = lower(mobility.country_name)
        and cases.report_date = mobility.report_date
    left join indicators
        on lower(cases.country_name) = lower(indicators.country_name)
)

select
    *,
    case when population > 0
         then confirmed_cases / population * 100000
         else null end as cases_per_100k,
    case when population > 0
         then confirmed_deaths / population * 100000
         else null end as deaths_per_100k,
    case when confirmed_cases > 0
         then confirmed_deaths / confirmed_cases
         else null end as case_fatality_rate
from joined
