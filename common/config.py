"""Environment-driven configuration shared by every Python component
(ETL scripts, EDA tooling, the API, and the dashboard) so credentials and
connection settings live in one place instead of being duplicated."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class SnowflakeConfig:
    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str
    schema: str
    marketplace_database: str
    marketplace_schema: str


@dataclass(frozen=True)
class MongoConfig:
    uri: str
    database: str


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill in your credentials."
        )
    return value


def load_snowflake_config() -> SnowflakeConfig:
    return SnowflakeConfig(
        account=_require("SNOWFLAKE_ACCOUNT"),
        user=_require("SNOWFLAKE_USER"),
        password=_require("SNOWFLAKE_PASSWORD"),
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COVID_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "COVID19_PLATFORM"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "GOLD"),
        marketplace_database=os.environ.get(
            "SNOWFLAKE_MARKETPLACE_DATABASE", "COVID19_EPIDEMIOLOGICAL_DATA"
        ),
        marketplace_schema=os.environ.get("SNOWFLAKE_MARKETPLACE_SCHEMA", "PUBLIC"),
    )


def load_mongo_config() -> MongoConfig:
    return MongoConfig(
        uri=os.environ.get("MONGO_URI", "mongodb://localhost:27017"),
        database=os.environ.get("MONGO_DATABASE", "covid_platform"),
    )
