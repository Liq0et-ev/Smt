# Assignment progress checklist

- [x] Task 1 — Snowflake Marketplace dataset + Resource Monitors (`COVID19_EPIDEMIOLOGICAL_DATA`, 44 tables acquired; `COVID_WH_MONITOR` created and attached to `COVID_WH`; Bronze/Silver/Gold schemas)
- [~] Task 2 — Data Exploration and Enhancement — SQL EDA, Python augmentation, and dbt project all written and pushed. **Python connector auth resolved** (switched to key-pair auth with explicit `authenticator="SNOWFLAKE_JWT"` -- see `docs/tasks/task2_data_exploration_and_enhancement.md`); Tier 1 survey verified against all 43 live tables. Bronze augmentation + `dbt run`/`dbt test` still to be run against live data to fully close this out.
- [x] Task 3 — NoSQL (MongoDB) schema design — **verified**: `docker compose up -d mongo` + `python -m mongo.init_collections` run successfully, all three collections (`annotations`, `supplementary_sources`, `user_preferences`) created with validators and indexes; independent of the Task 2 blocker
- [ ] Task 4 — API development (FastAPI) — not started
- [ ] Task 5 — Interactive visualization (Dash/Plotly) + annotations bonus — not started
- [ ] Task 6 — Forecasting + clustering bonus — not started
- [x] Task 7 — Snowflake performance optimization — **verified**: clustered `GOLD.JHU_COUNTRY_DAILY` scans ~2.2x less data and runs ~5.3x faster than raw `JHU_COVID_19`, confirmed by Snowflake's own Query Profile ("Filter with clustering key")
- [ ] Task 8 — API caching — not started
- [x] Task 9 — Pattern recognition (MATCH_RECOGNIZE) — **verified**: 416 waves + 2,986 surges detected against live data; surge detection independently rediscovered the real Omicron wave timing (Dec 2021-Mar 2022). Note: this account's `MATCH_RECOGNIZE` needs `LAG()` instead of the standard `PREV()` navigation function -- documented in `docs/tasks/task9_pattern_recognition.md`
- [ ] Task 10 — GitHub repo + README + deployment docs — partially in place (per-task docs, docker-compose.yml started); full deployment README pending
- [ ] Final report (PDF/Word) with insights — not started
