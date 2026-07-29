"""Task 3: NoSQL data modeling.

Creates the MongoDB collections used to store supplementary data that
doesn't belong in Snowflake -- user annotations/comments on specific
data points, and extra sources not present in the Marketplace dataset.
Each collection gets a $jsonSchema validator: MongoDB is schema-flexible
by default, but for a project like this (an API contract other code
depends on) an enforced *minimum* shape is worth having -- it's the
same reasoning as the dbt schema tests on the Snowflake side, just
applied to the NoSQL store instead of skipped because "NoSQL means no
schema."

Usage:
    python -m mongo.init_collections
"""
import logging
from datetime import datetime, timezone

from pymongo import ASCENDING, MongoClient, TEXT

from common.config import load_mongo_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


ANNOTATIONS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["scope", "comment", "created_at"],
        "properties": {
            "scope": {
                "bsonType": "object",
                "required": ["iso_code", "metric"],
                "properties": {
                    # iso_code is the join key back to Snowflake (JHU_COVID_19.ISO3166_1,
                    # OWID_VACCINATIONS.ISO3166_1, etc.) -- this is what actually ties
                    # the two databases together for the API (Task 4).
                    "iso_code": {"bsonType": "string", "description": "ISO 3166-1 country code, e.g. 'US'"},
                    "country_name": {"bsonType": "string"},
                    "metric": {
                        "bsonType": "string",
                        "enum": ["confirmed_cases", "confirmed_deaths", "vaccinations", "mobility", "other"],
                    },
                    "date": {"bsonType": ["date", "null"]},
                },
            },
            "author": {"bsonType": "string"},
            "comment": {"bsonType": "string", "minLength": 1, "maxLength": 2000},
            "tags": {"bsonType": "array", "items": {"bsonType": "string"}},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": ["date", "null"]},
        },
    }
}

SUPPLEMENTARY_SOURCES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["iso_code", "title", "url", "created_at"],
        "properties": {
            "iso_code": {"bsonType": "string"},
            "country_name": {"bsonType": "string"},
            "title": {"bsonType": "string", "minLength": 1},
            "url": {"bsonType": "string"},
            "description": {"bsonType": "string"},
            "source_type": {
                "bsonType": "string",
                "enum": ["news", "government", "research", "other"],
            },
            "added_by": {"bsonType": "string"},
            "created_at": {"bsonType": "date"},
        },
    }
}

USER_PREFERENCES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["user_id"],
        "properties": {
            "user_id": {"bsonType": "string"},
            "default_country_iso": {"bsonType": "string"},
            "favorite_metrics": {"bsonType": "array", "items": {"bsonType": "string"}},
            "theme": {"bsonType": "string", "enum": ["light", "dark"]},
            "updated_at": {"bsonType": ["date", "null"]},
        },
    }
}


def get_client() -> MongoClient:
    config = load_mongo_config()
    return MongoClient(config.uri)


def create_collection(db, name: str, validator: dict) -> None:
    if name in db.list_collection_names():
        logger.info("Collection %s already exists -- updating validator only", name)
        db.command("collMod", name, validator=validator, validationLevel="moderate")
        return
    db.create_collection(name, validator=validator, validationLevel="moderate")
    logger.info("Created collection %s", name)


def main() -> None:
    config = load_mongo_config()
    client = get_client()
    db = client[config.database]

    create_collection(db, "annotations", ANNOTATIONS_VALIDATOR)
    create_collection(db, "supplementary_sources", SUPPLEMENTARY_SOURCES_VALIDATOR)
    create_collection(db, "user_preferences", USER_PREFERENCES_VALIDATOR)

    # Indexes: scope.iso_code + scope.metric + scope.date is the lookup the
    # API will do constantly ("give me all annotations for US confirmed_cases
    # around this date") -- a compound index makes that fast instead of a
    # full collection scan. A text index on comment supports free-text search.
    db.annotations.create_index(
        [("scope.iso_code", ASCENDING), ("scope.metric", ASCENDING), ("scope.date", ASCENDING)]
    )
    db.annotations.create_index([("comment", TEXT)])

    db.supplementary_sources.create_index([("iso_code", ASCENDING)])
    db.user_preferences.create_index([("user_id", ASCENDING)], unique=True)

    logger.info("Done. Collections: %s", db.list_collection_names())
    client.close()


if __name__ == "__main__":
    main()
