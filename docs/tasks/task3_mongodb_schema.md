# Task 3 — Data Modeling in NoSQL (MongoDB)

## Why MongoDB, and for what specifically

Snowflake holds the structured, given/augmented COVID-19 data (Tasks 1-2).
MongoDB holds everything that's **user-generated, unstructured, or not
present in the Marketplace dataset at all**: annotations/comments on
specific data points (Task 5 bonus), and supplementary sources someone
adds by hand. This is a deliberate polyglot-persistence split, not two
databases doing the same job — Snowflake is for querying/aggregating
millions of rows fast; MongoDB is for flexible, low-volume,
frequently-changing-shape documents where a rigid SQL schema would be
awkward (e.g. a comment might have tags, or not; a source might have a
description, or not).

## Collections

### `annotations`
The core collection — a user's comment/annotation tied to a specific
point in the Snowflake data (Task 5's bonus: "allow users to add
annotations or comments, which are then stored in the NoSQL DB").

```json
{
  "_id": "ObjectId(...)",
  "scope": {
    "iso_code": "US",
    "country_name": "United States",
    "metric": "confirmed_cases",
    "date": "2020-03-15T00:00:00Z"
  },
  "author": "vladislavebert@gmail.com",
  "comment": "Sharp jump here coincides with expanded testing capacity, not necessarily a real spike in transmission.",
  "tags": ["testing", "data-quality"],
  "created_at": "2026-07-29T10:00:00Z",
  "updated_at": null
}
```

- **`scope.iso_code`** is the deliberate join key back to Snowflake —
  the same ISO 3166-1 code used throughout the dbt models
  (`JHU_COVID_19.ISO3166_1`, `OWID_VACCINATIONS.ISO3166_1`, etc.). This
  is what lets the API (Task 4) fetch "the Snowflake numbers for country
  X" and "the MongoDB annotations for country X" with one shared key,
  rather than two databases that can't be correlated.
- **`scope.metric`** is constrained to a fixed enum
  (`confirmed_cases`/`confirmed_deaths`/`vaccinations`/`mobility`/`other`)
  so annotations can be filtered per-chart in the dashboard.
- **`scope.date`** is optional (nullable) — an annotation can be about a
  single day or about a country generally.

### `supplementary_sources`
Additional sources not found in Snowflake (e.g. a news article, a local
government report) — the other half of Task 3's brief ("additional
sources not found in Snowflake").

```json
{
  "_id": "ObjectId(...)",
  "iso_code": "DE",
  "country_name": "Germany",
  "title": "RKI weekly report, week 14",
  "url": "https://www.rki.de/...",
  "description": "Detailed regional breakdown not present in the Marketplace RKI table.",
  "source_type": "government",
  "added_by": "vladislavebert@gmail.com",
  "created_at": "2026-07-29T10:00:00Z"
}
```

### `user_preferences`
Mentioned in the assignment's technology list ("MongoDB for storing user
preferences, comments, or supplementary semi-structured data") — small,
per-user dashboard settings.

```json
{
  "_id": "ObjectId(...)",
  "user_id": "vladislavebert@gmail.com",
  "default_country_iso": "US",
  "favorite_metrics": ["confirmed_cases", "vaccinations"],
  "theme": "dark",
  "updated_at": "2026-07-29T10:00:00Z"
}
```

## Enforcing a minimum shape despite MongoDB being "schema-flexible"

Each collection is created with a `$jsonSchema` validator
([`mongo/init_collections.py`](../../mongo/init_collections.py)) —
MongoDB doesn't *require* a schema, but this project's API depends on a
predictable document shape, so a validator enforces required
fields/types at write time (`validationLevel: moderate`, so existing
documents aren't retroactively broken if the schema evolves). This is
the same instinct as the dbt schema tests on the Snowflake side
(Task 2), just applied on the NoSQL side instead of being skipped
because "NoSQL means no rules."

## Indexes

- `annotations`: compound index on `(scope.iso_code, scope.metric, scope.date)`
  — the exact lookup pattern the API will do constantly ("annotations for
  US confirmed_cases around this date"), avoiding a full collection scan.
- `annotations`: text index on `comment` — supports free-text search.
- `supplementary_sources`: index on `iso_code`.
- `user_preferences`: unique index on `user_id`.

## How to run this

```bash
docker compose up -d mongo
pip install -r requirements.txt      # includes pymongo now
python -m mongo.init_collections
```

Verify:
```bash
docker exec -it covid_platform_mongo mongosh covid_platform --eval "db.getCollectionNames()"
```
Should print `[ 'annotations', 'supplementary_sources', 'user_preferences' ]`.

This part of the project has **no dependency on the Snowflake Python
connector** — it runs entirely locally against Docker, independent of
the Snowflake connectivity issue tracked in Task 2.
