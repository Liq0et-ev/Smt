# Task 5 — Interactive Visualization Dashboard (Dash/Plotly)

## What it does

A single-page Dash app that lets you pick a country and see its COVID-19
story: current totals, case/death trends with detected waves overlaid,
vaccination progress, a JHU-vs-WHO data-quality cross-check, and
(bonus) a place to read and add annotations on that country's data.

The dashboard **only talks to the FastAPI backend (Task 4) over HTTP** --
it never queries Snowflake or MongoDB directly. That's a deliberate
architectural choice: the API is the single point of access to both
databases (per the assignment's own diagram), and the dashboard is just
another client of it, same as `curl` or Swagger UI were during Task 4's
testing.

## Layout

- **Country dropdown** -- populated once at startup from `GET /countries`.
- **Date range picker** -- optional, passed through to `GET /daily`'s
  `start_date`/`end_date` params.
- **Summary stat cards** -- latest date, cases, deaths, case fatality
  rate, vaccination %, and the augmented indicators (median age, GDP per
  capita, HDI) from `GET /summary`.
- **Cases & deaths chart** -- dual-axis line chart from `GET /daily`,
  with each detected wave (Task 9's `MATCH_RECOGNIZE` pattern, run live
  per country via `GET /waves`) shaded as a highlighted region on top --
  makes the pattern-recognition work visible, not just a number in a
  table.
- **Vaccination progress chart** -- from the same `/daily` payload.
- **Cross-check chart** -- JHU vs. WHO reported cases side by side, from
  `GET /cross-check` (Task 2/9's data-quality mart).
- **Annotations panel (bonus)** -- lists existing annotations for the
  selected country (`GET /annotations`) and a form to add a new one
  (`POST /annotations`), stored in MongoDB (Task 3) through the API.

## Design notes

- **Two separate callbacks, connected by a `dcc.Store`.** The main chart
  callback fires on country/date-range changes. The annotations list has
  its own callback, fired by either a country change *or* a
  `dcc.Store` "refresh token" that the submit-annotation callback bumps
  after a successful POST. This avoids two callbacks fighting over the
  same output, and avoids re-fetching all four chart endpoints just
  because someone added an annotation.
- **Verified before handing off**, same practice as Task 4: every
  callback function was exercised directly with mocked
  `dashboard.api_client` responses (`unittest.mock.patch`) to catch
  layout/field-mapping bugs before running against the live API --
  see the assertions each callback needs to satisfy (card count, chart
  trace count, wave shading, annotation refresh behavior, the
  empty-comment guard) rather than just eyeballing it in a browser.

## How to run

**Locally (venv, API already running separately):**
```bash
python -m dashboard.app
```
Then open `http://localhost:8050`. Needs `uvicorn api.main:app --reload`
running in another terminal first (same as Task 4) -- the dashboard
fetches the country list once at startup, so start the API first.

**Via Docker Compose** (starts MongoDB, the API, and the dashboard together):
```bash
docker compose up -d --build
```
The dashboard container reaches the API at `http://api:8000` (Docker's
internal network), not `localhost` -- same pattern MongoDB's connection
string already used.
