# Task 4 — API Development with Python (FastAPI)

## What it does

A FastAPI backend that ties together both databases, per the assignment's
explicit requirements:

- **"Query Snowflake for data based on user inputs"** — every
  `/countries/*` endpoint takes user input (a country ISO code in the
  URL, optional date-range query params) and queries
  `COVID19_PLATFORM.GOLD` (Task 2's dbt-built layer) accordingly.
- **"Interact with the NoSQL database for relevant additional data or
  metadata"** — `/countries/{iso_code}/annotations` reads/writes
  MongoDB (Task 3's `annotations` collection).
- **"Perform any on-the-fly data processing required"** — `/summary`
  computes latest totals/rates per request rather than from a
  pre-materialized table, and `/waves` runs Task 9's `MATCH_RECOGNIZE`
  wave-detection pattern live, scoped to one country, on every request.

## Endpoints

| Method | Path | Source | Purpose |
|---|---|---|---|
| GET | `/countries` | Snowflake | List all countries in the Gold layer |
| GET | `/countries/{iso_code}/daily` | Snowflake | Time series, optional `start_date`/`end_date` |
| GET | `/countries/{iso_code}/summary` | Snowflake | On-the-fly latest totals/rates |
| GET | `/countries/{iso_code}/cross-check` | Snowflake | JHU vs. WHO agreement (Task 2/9's `jhu_who_cross_check` mart) |
| GET | `/countries/{iso_code}/waves` | Snowflake | Live `MATCH_RECOGNIZE` wave detection (Task 9), scoped to one country |
| GET | `/countries/{iso_code}/annotations` | MongoDB | List annotations, optional `?metric=` filter |
| POST | `/countries/{iso_code}/annotations` | MongoDB | Create an annotation (Task 5 bonus) |
| GET | `/health` | — | Health check |

Interactive docs (Swagger UI) at `/docs` once running.

## Design notes

- **SQL injection**: every endpoint takes user-controlled input (country
  code, dates), so `common/snowflake_client.py`'s `query_to_dataframe()`
  was extended to accept bound `params` (`%(name)s` placeholders) instead
  of string-interpolating values into SQL — required, not optional, once
  user input reaches a query.
- **`/waves` reuses `sql/06_pattern_recognition_match_recognize.sql`'s
  exact pattern** (parameterized to one country instead of running
  across all of them), rather than duplicating the logic differently —
  demonstrates the same `MATCH_RECOGNIZE` approach validated in Task 9,
  now exposed as a live, on-demand API capability instead of only a
  standalone SQL script.
- **Clustering key payoff** (Task 7): `/daily`'s filter
  (`ISO_CODE = ... AND REPORT_DATE BETWEEN ...`) is exactly the pattern
  `GOLD.JHU_COUNTRY_DAILY`'s clustering key was chosen for — this
  endpoint is a direct beneficiary of that earlier optimization work.
- **Verified before handing off**: every endpoint was functionally
  tested locally (mocked Snowflake/MongoDB responses via
  `fastapi.testclient.TestClient`) to catch field-mapping/serialization
  bugs before running against the live account, given how much
  back-and-forth the SQL scripts needed earlier in this project.

## How to run

**Locally (venv):**
```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
Then open `http://localhost:8000/docs`.

**Via Docker Compose** (also starts MongoDB):
```bash
docker compose up -d --build
```
The API container mounts your Snowflake private key read-only from the
host path in `SNOWFLAKE_PRIVATE_KEY_PATH` (`.env`) and connects to the
`mongo` container directly (not `localhost`) via Docker's internal
network.

## Known limitation: daily series for state-reported countries

`/daily` (and `/waves`, which reuses the same underlying series) for
countries JHU tracks at state/province granularity in this Marketplace
mirror (the US being the clearest example) undercounts on any given day,
because not every state reports on every date -- there's no single date
where all ~60 US states have a row simultaneously, so each day's summed
total is a partial count. `/summary` sidesteps this (see its docstring:
it sums each state's own highest-ever recorded value instead of summing
*by date*), but that trick only works for a single "current total," not
a day-by-day series -- a correct daily series would need each state's
cumulative count forward-filled onto the days it didn't report, which is
a real gap-filling problem (`LAST_VALUE(...) IGNORE NULLS` per state,
then re-sum per date) left undone here as an intentional scope
boundary. Documenting it here as a known data-quality finding rather
than silently leaving it unexplained -- it's a legitimate, citable
insight for the final report (JHU's per-country reporting granularity
is inconsistent both across countries and over time).

## Try it

```bash
curl http://localhost:8000/countries | head -c 300
curl http://localhost:8000/countries/US/summary
curl http://localhost:8000/countries/US/waves
curl -X POST http://localhost:8000/countries/US/annotations \
  -H "Content-Type: application/json" \
  -d '{"metric": "confirmed_cases", "comment": "Testing surge in early 2021 inflates confirmed cases independent of true transmission."}'
```
