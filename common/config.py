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
    role: str
    warehouse: str
    database: str
    schema: str
    marketplace_database: str
    marketplace_schema: str
    # Auth: exactly one of these is used. Key-pair (private_key_path) is
    # preferred when set -- it sidesteps password/MFA-related auth issues
    # entirely and is the standard approach for non-interactive scripts.
    password: str | None = None
    private_key_path: str | None = None
    private_key_passphrase: str | None = None


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
    private_key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
    password = os.environ.get("SNOWFLAKE_PASSWORD")
    if not private_key_path and not password:
        raise RuntimeError(
            "Set either SNOWFLAKE_PRIVATE_KEY_PATH (key-pair auth, preferred) "
            "or SNOWFLAKE_PASSWORD in .env."
        )

    return SnowflakeConfig(
        account=_require("SNOWFLAKE_ACCOUNT"),
        user=_require("SNOWFLAKE_USER"),
        password=password,
        private_key_path=private_key_path,
        private_key_passphrase=os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"),
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
