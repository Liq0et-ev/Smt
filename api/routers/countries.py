"""Task 4: Snowflake-backed endpoints. Queries COVID19_PLATFORM.GOLD
(built by dbt, Task 2) based on user input (country code, date range),
including on-the-fly aggregation/pattern-recognition run per request."""
import logging

from fastapi import APIRouter, HTTPException, Query

from api.schemas import Country, CountryDailyRecord, CountrySummary, CrossCheckRecord, WaveRecord
from common.snowflake_client import query_to_dataframe

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/countries", tags=["countries"])

GOLD = "COVID19_PLATFORM.GOLD"


@router.get("", response_model=list[Country])
def list_countries():
    """All countries present in the Gold layer -- powers the dashboard's
    country picker (Task 5)."""
    df = query_to_dataframe(
        f"""
        SELECT ISO_CODE, MAX(COUNTRY_NAME) AS COUNTRY_NAME, MAX(CONTINENT) AS CONTINENT
        FROM {GOLD}.COUNTRY_DAILY_ENRICHED
        GROUP BY ISO_CODE
        ORDER BY COUNTRY_NAME
        """
    )
    return [
        Country(iso_code=r.ISO_CODE, country_name=r.COUNTRY_NAME, continent=r.CONTINENT)
        for r in df.itertuples()
    ]


@router.get("/{iso_code}/daily", response_model=list[CountryDailyRecord])
def get_country_daily(
    iso_code: str,
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
):
    """Time series for one country, optionally bounded by date range --
    "query Snowflake for data based on user inputs" (Task 4). Benefits
    directly from the (ISO_CODE, REPORT_DATE) clustering key set up in
    Task 7: this is exactly the filter/sort pattern it was chosen for."""
    conditions = ["ISO_CODE = %(iso_code)s"]
    params: dict = {"iso_code": iso_code.upper()}
    if start_date:
        conditions.append("REPORT_DATE >= %(start_date)s")
        params["start_date"] = start_date
    if end_date:
        conditions.append("REPORT_DATE <= %(end_date)s")
        params["end_date"] = end_date

    sql = f"""
        SELECT ISO_CODE, COUNTRY_NAME, REPORT_DATE, CONFIRMED_CASES, CONFIRMED_DEATHS,
               TOTAL_VACCINATIONS, PEOPLE_FULLY_VACCINATED, PEOPLE_FULLY_VACCINATED_PER_HUNDRED,
               TOTAL_POPULATION, CASES_PER_100K, DEATHS_PER_100K, CASE_FATALITY_RATE
        FROM {GOLD}.COUNTRY_DAILY_ENRICHED
        WHERE {' AND '.join(conditions)}
        ORDER BY REPORT_DATE
    """
    df = query_to_dataframe(sql, params=params)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for country '{iso_code}'")
    return [
        CountryDailyRecord(
            iso_code=r.ISO_CODE,
            country_name=r.COUNTRY_NAME,
            report_date=r.REPORT_DATE,
            confirmed_cases=r.CONFIRMED_CASES,
            confirmed_deaths=r.CONFIRMED_DEATHS,
            total_vaccinations=r.TOTAL_VACCINATIONS,
            people_fully_vaccinated=r.PEOPLE_FULLY_VACCINATED,
            people_fully_vaccinated_per_hundred=r.PEOPLE_FULLY_VACCINATED_PER_HUNDRED,
            total_population=r.TOTAL_POPULATION,
            cases_per_100k=r.CASES_PER_100K,
            deaths_per_100k=r.DEATHS_PER_100K,
            case_fatality_rate=r.CASE_FATALITY_RATE,
        )
        for r in df.itertuples()
    ]


@router.get("/{iso_code}/summary", response_model=CountrySummary)
def get_country_summary(iso_code: str):
    """On-the-fly aggregation (Task 4 requirement): the latest known
    totals/rates for a country, computed per request rather than stored
    -- a small enough query to run live instead of needing a
    pre-materialized "latest" table.

    Deliberately MAX()s each cumulative metric independently rather than
    picking "the row for the most recent date": JHU's own data collection
    wound down through early 2023, so on the actual last date in the
    dataset only a handful of countries/regions still had a row at all --
    picking that exact row understated cumulative totals by orders of
    magnitude for countries reported at state/province granularity (e.g.
    the US). Since confirmed_cases/deaths are non-decreasing cumulative
    counts, the highest value ever recorded is the correct "latest known
    total," robust to which specific rows are sparse near the end."""
    df = query_to_dataframe(
        f"""
        SELECT
            ISO_CODE,
            MAX(COUNTRY_NAME) AS COUNTRY_NAME,
            MAX(REPORT_DATE) AS LATEST_DATE,
            MAX(TOTAL_POPULATION) AS TOTAL_POPULATION,
            MAX(CONFIRMED_CASES) AS LATEST_CONFIRMED_CASES,
            MAX(CONFIRMED_DEATHS) AS LATEST_CONFIRMED_DEATHS,
            MAX(PEOPLE_FULLY_VACCINATED_PER_HUNDRED) AS LATEST_PEOPLE_FULLY_VACCINATED_PER_HUNDRED,
            MAX(MEDIAN_AGE) AS MEDIAN_AGE,
            MAX(GDP_PER_CAPITA) AS GDP_PER_CAPITA,
            MAX(HUMAN_DEVELOPMENT_INDEX) AS HUMAN_DEVELOPMENT_INDEX
        FROM {GOLD}.COUNTRY_DAILY_ENRICHED
        WHERE ISO_CODE = %(iso_code)s
        GROUP BY ISO_CODE
        """,
        params={"iso_code": iso_code.upper()},
    )
    if df.empty or df.iloc[0].LATEST_CONFIRMED_CASES is None:
        raise HTTPException(status_code=404, detail=f"No data for country '{iso_code}'")
    r = df.iloc[0]
    case_fatality_rate = (
        r.LATEST_CONFIRMED_DEATHS / r.LATEST_CONFIRMED_CASES
        if r.LATEST_CONFIRMED_CASES else None
    )
    return CountrySummary(
        iso_code=r.ISO_CODE,
        country_name=r.COUNTRY_NAME,
        latest_date=r.LATEST_DATE,
        total_population=r.TOTAL_POPULATION,
        latest_confirmed_cases=r.LATEST_CONFIRMED_CASES,
        latest_confirmed_deaths=r.LATEST_CONFIRMED_DEATHS,
        latest_case_fatality_rate=case_fatality_rate,
        latest_people_fully_vaccinated_per_hundred=r.LATEST_PEOPLE_FULLY_VACCINATED_PER_HUNDRED,
        median_age=r.MEDIAN_AGE,
        gdp_per_capita=r.GDP_PER_CAPITA,
        human_development_index=r.HUMAN_DEVELOPMENT_INDEX,
    )


@router.get("/{iso_code}/cross-check", response_model=list[CrossCheckRecord])
def get_country_cross_check(iso_code: str):
    """JHU vs. WHO agreement for this country (Task 2/9's
    jhu_who_cross_check mart) -- a data-quality/trust signal exposed
    directly through the API."""
    df = query_to_dataframe(
        f"""
        SELECT ISO_CODE, COUNTRY_NAME, REPORT_DATE, JHU_CASES, WHO_TOTAL_CASES,
               CASE_COUNT_DIFF, JHU_DEATHS, WHO_DEATHS, DEATH_COUNT_DIFF
        FROM {GOLD}.JHU_WHO_CROSS_CHECK
        WHERE ISO_CODE = %(iso_code)s
        ORDER BY REPORT_DATE
        """,
        params={"iso_code": iso_code.upper()},
    )
    return [
        CrossCheckRecord(
            iso_code=r.ISO_CODE,
            country_name=r.COUNTRY_NAME,
            report_date=r.REPORT_DATE,
            jhu_cases=r.JHU_CASES,
            who_total_cases=r.WHO_TOTAL_CASES,
            case_count_diff=r.CASE_COUNT_DIFF,
            jhu_deaths=r.JHU_DEATHS,
            who_deaths=r.WHO_DEATHS,
            death_count_diff=r.DEATH_COUNT_DIFF,
        )
        for r in df.itertuples()
    ]


@router.get("/{iso_code}/waves", response_model=list[WaveRecord])
def get_country_waves(iso_code: str):
    """Task 9's MATCH_RECOGNIZE wave-detection pattern, run live and
    scoped to one country -- genuine on-the-fly SQL processing per
    request (not a pre-computed table), directly reusing the pattern
    from sql/06_pattern_recognition_match_recognize.sql."""
    sql = """
        WITH country_daily AS (
            SELECT ISO3166_1 AS ISO_CODE, COUNTRY_REGION, DATE, DIFFERENCE AS NEW_CASES
            FROM COVID19_EPIDEMIOLOGICAL_DATA.PUBLIC.JHU_COVID_19
            WHERE PROVINCE_STATE IS NULL AND COUNTY IS NULL
              AND CASE_TYPE = 'Confirmed' AND DATE IS NOT NULL
              AND ISO3166_1 = %(iso_code)s
        ),
        smoothed AS (
            SELECT ISO_CODE, COUNTRY_REGION, DATE,
                   AVG(NEW_CASES) OVER (
                       PARTITION BY ISO_CODE ORDER BY DATE
                       ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                   ) AS NEW_CASES_7D_AVG
            FROM country_daily
        )
        SELECT *
        FROM smoothed
        MATCH_RECOGNIZE (
            PARTITION BY ISO_CODE
            ORDER BY DATE
            MEASURES
                FIRST(COUNTRY_REGION) AS COUNTRY_NAME,
                MATCH_NUMBER()        AS WAVE_NUMBER,
                FIRST(DATE)           AS WAVE_START,
                LAST(UP.DATE)         AS PEAK_DATE,
                LAST(DATE)            AS WAVE_END,
                COUNT(UP.*)           AS RISING_DAYS,
                COUNT(DOWN.*)         AS FALLING_DAYS,
                MAX(NEW_CASES_7D_AVG) AS PEAK_7D_AVG_NEW_CASES
            ONE ROW PER MATCH
            AFTER MATCH SKIP PAST LAST ROW
            PATTERN (UP{5,} DOWN{5,})
            DEFINE
                UP   AS NEW_CASES_7D_AVG > LAG(NEW_CASES_7D_AVG),
                DOWN AS NEW_CASES_7D_AVG <= LAG(NEW_CASES_7D_AVG)
        )
        ORDER BY WAVE_START
    """
    df = query_to_dataframe(sql, params={"iso_code": iso_code.upper()})
    return [
        WaveRecord(
            country_name=r.COUNTRY_NAME,
            wave_number=r.WAVE_NUMBER,
            wave_start=r.WAVE_START,
            peak_date=r.PEAK_DATE,
            wave_end=r.WAVE_END,
            rising_days=r.RISING_DAYS,
            falling_days=r.FALLING_DAYS,
            peak_7d_avg_new_cases=r.PEAK_7D_AVG_NEW_CASES,
        )
        for r in df.itertuples()
    ]
