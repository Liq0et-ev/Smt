"""Pydantic response/request models for the API (Task 4)."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class Country(BaseModel):
    iso_code: str
    country_name: str | None = None
    continent: str | None = None


class CountryDailyRecord(BaseModel):
    iso_code: str
    country_name: str | None = None
    report_date: date
    confirmed_cases: float | None = None
    confirmed_deaths: float | None = None
    total_vaccinations: float | None = None
    people_fully_vaccinated: float | None = None
    people_fully_vaccinated_per_hundred: float | None = None
    total_population: float | None = None
    cases_per_100k: float | None = None
    deaths_per_100k: float | None = None
    case_fatality_rate: float | None = None


class CountrySummary(BaseModel):
    """On-the-fly aggregation: latest known totals + rates for a country."""
    iso_code: str
    country_name: str | None = None
    latest_date: date | None = None
    total_population: float | None = None
    latest_confirmed_cases: float | None = None
    latest_confirmed_deaths: float | None = None
    latest_case_fatality_rate: float | None = None
    latest_people_fully_vaccinated_per_hundred: float | None = None
    median_age: float | None = None
    gdp_per_capita: float | None = None
    human_development_index: float | None = None


class CrossCheckRecord(BaseModel):
    iso_code: str
    country_name: str | None = None
    report_date: date
    jhu_cases: float | None = None
    who_total_cases: float | None = None
    case_count_diff: float | None = None
    jhu_deaths: float | None = None
    who_deaths: float | None = None
    death_count_diff: float | None = None


class WaveRecord(BaseModel):
    """Task 9's MATCH_RECOGNIZE wave-detection output, run on demand for
    a single country (see routers/countries.py)."""
    country_name: str | None = None
    wave_number: int
    wave_start: date
    peak_date: date | None = None
    wave_end: date
    rising_days: int
    falling_days: int
    peak_7d_avg_new_cases: float | None = None


class AnnotationCreate(BaseModel):
    metric: str = Field(..., description="confirmed_cases | confirmed_deaths | vaccinations | mobility | other")
    comment: str = Field(..., min_length=1, max_length=2000)
    country_name: str | None = None
    date: datetime | None = None
    author: str | None = None
    tags: list[str] = []


class Annotation(AnnotationCreate):
    id: str
    iso_code: str
    created_at: datetime
