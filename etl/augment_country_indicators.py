"""Task 2 augmentation: enrich the Snowflake COVID-19 dataset with
country-level demographic/economic indicators that it does NOT contain
(the Marketplace dataset's own DEMOGRAPHICS table is US-county-level only,
see docs/tasks/task1_marketplace_and_resource_monitors.md).

Source: Our World in Data's public, freely-licensed COVID-19 dataset,
which carries per-country demographic/economic indicators (population,
median age, GDP per capita, hospital beds per thousand, human development
index, etc.) sourced from the World Bank / UN. This is downloaded fresh
each run rather than committed to the repo, so the platform always
augments against current figures and stays reproducible on any machine
without needing a Kaggle account/API key.

Usage:
    python -m etl.augment_country_indicators
"""
import logging

import pandas as pd
import requests

from common.config import load_snowflake_config
from common.snowflake_client import execute, upload_dataframe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OWID_LATEST_URL = "https://covid.ourworldindata.org/data/latest/owid-covid-latest.csv"

# Demographic/economic columns we augment with (deliberately excludes OWID's
# own case/death/vaccination counts -- those we already have natively in
# Snowflake via JHU_COVID_19 / ECDC_GLOBAL / OWID_VACCINATIONS, and mixing
# duplicate sources for the same metric would just create a reconciliation
# problem rather than adding information).
INDICATOR_COLUMNS = [
    "iso_code",
    "continent",
    "location",
    "population",
    "population_density",
    "median_age",
    "aged_65_older",
    "aged_70_older",
    "gdp_per_capita",
    "extreme_poverty",
    "cardiovasc_death_rate",
    "diabetes_prevalence",
    "female_smokers",
    "male_smokers",
    "handwashing_facilities",
    "hospital_beds_per_thousand",
    "life_expectancy",
    "human_development_index",
]

RAW_TABLE = "COUNTRY_INDICATORS"
ANALYTICS_VIEW = "COUNTRY_DAILY_ENRICHED"


def fetch_country_indicators() -> pd.DataFrame:
    logger.info("Downloading OWID country indicators from %s", OWID_LATEST_URL)
    df = pd.read_csv(OWID_LATEST_URL, usecols=INDICATOR_COLUMNS)

    # OWID includes continent/world/income-group aggregate rows (iso_code
    # like 'OWID_WRL', 'OWID_EUR') which have no ISO-3166 country code and
    # would break a country-level join -- drop them.
    df = df[~df["iso_code"].str.startswith("OWID_", na=True)]
    df = df.dropna(subset=["iso_code"])

    logger.info("Fetched %d country-level indicator rows", len(df))
    return df


def load_into_snowflake(df: pd.DataFrame) -> None:
    config = load_snowflake_config()
    logger.info(
        "Uploading to %s.%s.%s", config.database, "RAW", RAW_TABLE
    )
    upload_dataframe(
        df,
        table_name=RAW_TABLE,
        database=config.database,
        schema="RAW",
        config=config,
        overwrite=True,
    )


def main() -> None:
    df = fetch_country_indicators()
    load_into_snowflake(df)
    logger.info("Done. Raw table: COVID19_PLATFORM.RAW.%s", RAW_TABLE)
    logger.info(
        "Next: run sql/04_build_analytics_layer.sql to join this against "
        "the core epidemiological tables and build %s.", ANALYTICS_VIEW
    )


if __name__ == "__main__":
    main()
