-- Gold: data-quality/insight mart -- how much do JHU_COVID_19 and
-- WHO_SITUATION_REPORTS actually agree on cases/deaths for the same
-- country and date? Two independent sources rarely match exactly; this
-- quantifies the gap rather than assuming one source is "correct" --
-- directly useful for the Task 2

with jhu as (
    select iso_code, country_name, report_date, confirmed_cases, confirmed_deaths
    from {{ ref('stg_jhu_covid_19') }}
),

who as (
    select iso_code, report_date, total_cases as who_total_cases, deaths as who_deaths
    from {{ ref('stg_who_situation_reports') }}
)

select
    jhu.iso_code,
    jhu.country_name,
    jhu.report_date,
    jhu.confirmed_cases   as jhu_cases,
    who.who_total_cases,
    jhu.confirmed_deaths  as jhu_deaths,
    who.who_deaths,
    jhu.confirmed_cases - who.who_total_cases  as case_count_diff,
    jhu.confirmed_deaths - who.who_deaths      as death_count_diff
from jhu
inner join who
    on jhu.iso_code = who.iso_code
    and jhu.report_date = who.report_date
