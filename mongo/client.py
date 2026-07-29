"""Thin MongoDB helper, mirroring common/snowflake_client.py's style so
the FastAPI backend (Task 4) has a consistent pattern for talking to
both databases."""
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection

from common.config import MongoConfig, load_mongo_config


@contextmanager
def get_client(config: MongoConfig | None = None):
    config = config or load_mongo_config()
    client = MongoClient(config.uri)
    try:
        yield client
    finally:
        client.close()


def get_collection(name: str, config: MongoConfig | None = None) -> Collection:
    """Note: returns a collection bound to a client that isn't explicitly
    closed here -- fine for short-lived scripts/tests. The FastAPI app
    (Task 4) will manage a single long-lived client instead of opening
    one per request."""
    config = config or load_mongo_config()
    client = MongoClient(config.uri)
    return client[config.database][name]


def insert_annotation(
    iso_code: str,
    metric: str,
    comment: str,
    country_name: str | None = None,
    date: datetime | None = None,
    author: str | None = None,
    tags: list[str] | None = None,
    config: MongoConfig | None = None,
) -> str:
    """Bonus (Task 5): store a user annotation/comment on a data point."""
    doc: dict[str, Any] = {
        "scope": {
            "iso_code": iso_code,
            "country_name": country_name,
            "metric": metric,
            "date": date,
        },
        "author": author,
        "comment": comment,
        "tags": tags or [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    }
    with get_client(config) as client:
        result = client[(config or load_mongo_config()).database]["annotations"].insert_one(doc)
        return str(result.inserted_id)


def get_annotations(
    iso_code: str, metric: str | None = None, config: MongoConfig | None = None
) -> list[dict]:
    """Read annotations for a given country (and optionally metric) --
    what the API (Task 4) calls when a client asks for a data point's
    supplementary comments alongside the Snowflake numbers."""
    query: dict[str, Any] = {"scope.iso_code": iso_code}
    if metric:
        query["scope.metric"] = metric
    with get_client(config) as client:
        docs = list(
            client[(config or load_mongo_config()).database]["annotations"].find(query)
        )
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs
