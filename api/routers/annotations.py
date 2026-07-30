"""Task 4: MongoDB-backed endpoints ("interact with the NoSQL database
for relevant additional data or metadata"). Also the backend for Task 5's
bonus -- users adding annotations/comments stored in MongoDB."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from api.schemas import Annotation, AnnotationCreate
from common.config import load_mongo_config
from mongo.client import get_client

router = APIRouter(prefix="/countries/{iso_code}/annotations", tags=["annotations"])


@router.get("", response_model=list[Annotation])
def list_annotations(iso_code: str, metric: str | None = None):
    query: dict = {"scope.iso_code": iso_code.upper()}
    if metric:
        query["scope.metric"] = metric

    config = load_mongo_config()
    with get_client(config) as client:
        docs = list(client[config.database]["annotations"].find(query).sort("created_at", -1))

    return [
        Annotation(
            id=str(doc["_id"]),
            iso_code=doc["scope"]["iso_code"],
            metric=doc["scope"]["metric"],
            country_name=doc["scope"].get("country_name"),
            date=doc["scope"].get("date"),
            comment=doc["comment"],
            author=doc.get("author"),
            tags=doc.get("tags", []),
            created_at=doc["created_at"],
        )
        for doc in docs
    ]


@router.post("", response_model=Annotation, status_code=201)
def create_annotation(iso_code: str, body: AnnotationCreate):
    """Task 5 bonus: store a user annotation/comment on a data point."""
    doc = {
        "scope": {
            "iso_code": iso_code.upper(),
            "country_name": body.country_name,
            "metric": body.metric,
            "date": body.date,
        },
        "comment": body.comment,
        "author": body.author,
        "tags": body.tags,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    }

    config = load_mongo_config()
    with get_client(config) as client:
        try:
            result = client[config.database]["annotations"].insert_one(doc)
        except Exception as e:
            # Most likely the $jsonSchema validator (mongo/init_collections.py)
            # rejecting a malformed document -- surface as a 400, not a 500.
            raise HTTPException(status_code=400, detail=f"Invalid annotation: {e}")

    return Annotation(
        id=str(result.inserted_id),
        iso_code=iso_code.upper(),
        metric=body.metric,
        country_name=body.country_name,
        date=body.date,
        comment=body.comment,
        author=body.author,
        tags=body.tags,
        created_at=doc["created_at"],
    )
