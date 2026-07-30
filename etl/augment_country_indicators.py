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

This script only handles the Python-side ingestion (HTTP fetch -> Bronze
table) -- it deliberately does NOT do any joining/cleaning. That happens
in dbt (see transform/), which builds Silver (cleaned/joined) and Gold
(consumption-ready) models on top of this Bronze table, per the Medallion
Architecture / dbt patterns from the bootcamp.

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

# Our World in Data publishes this same file to their own domain AND to
# their public GitHub repo (the website is effectively a mirror of the
# repo). Using the GitHub-hosted copy here since some restricted/managed
# networks allow github.com/raw.githubusercontent.com (needed for `git`
# itself) but block arbitrary other domains like ourworldindata.org.
OWID_LATEST_URL = (
    "https://raw.githubusercontent.com/owid/covid-19-data/master/"
    "public/data/latest/owid-covid-latest.csv"
)

# Demographic/economic columns we augment with. Deliberately excludes:
#   - OWID's own case/death/vaccination counts -- we already have those
#     natively via JHU_COVID_19 / WHO_SITUATION_REPORTS / OWID_VACCINATIONS
#   - "population" -- confirmed natively available, globally, via the
#     Marketplace's own DATABANK_DEMOGRAPHICS table (country-level; not to
#     be confused with the similarly-named but US-county-only DEMOGRAPHICS
#     table). No point re-fetching a metric we already have in Snowflake.
INDICATOR_COLUMNS = [
    "iso_code",
    "continent",
    "location",
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

BRONZE_TABLE = "COUNTRY_INDICATORS"


def fetch_country_indicators() -> pd.DataFrame:
    logger.info("Downloading OWID country indicators from %s", OWID_LATEST_URL)
    df = pd.read_csv(OWID_LATEST_URL, usecols=INDICATOR_COLUMNS)

    # OWID includes continent/world/income-group aggregate rows (iso_code
    # like 'OWID_WRL', 'OWID_EUR') which have no ISO-3166 country code and
    # would break a country-level join -- drop them.
    df = df[~df["iso_code"].str.startswith("OWID_", na=True)]
    df = df.dropna(subset=["iso_code"]).reset_index(drop=True)

    logger.info("Fetched %d country-level indicator rows", len(df))
    return df


def load_into_snowflake(df: pd.DataFrame) -> None:
    config = load_snowflake_config()
    logger.info(
        "Uploading to %s.%s.%s", config.database, "BRONZE", BRONZE_TABLE
    )
    upload_dataframe(
        df,
        table_name=BRONZE_TABLE,
        database=config.database,
        schema="BRONZE",
        config=config,
        overwrite=True,
    )


def main() -> None:
    df = fetch_country_indicators()
    load_into_snowflake(df)
    logger.info("Done. Bronze table: COVID19_PLATFORM.BRONZE.%s", BRONZE_TABLE)
    logger.info(
        "Next: run `dbt run` in transform/ to build the Silver (cleaned/"
        "joined) and Gold (consumption-ready) models on top of this table."
    )


if __name__ == "__main__":
    main()
