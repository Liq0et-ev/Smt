# Assignment progress checklist

- [x] Task 1 — Snowflake Marketplace dataset + Resource Monitors (`COVID19_EPIDEMIOLOGICAL_DATA`, 44 tables acquired; `COVID_WH_MONITOR` created and attached to `COVID_WH`; Bronze/Silver/Gold schemas)
- [~] Task 2 — Data Exploration and Enhancement — SQL EDA, Python augmentation, and dbt project all written and pushed; **blocked on verifying against live data** by a Snowflake Python-connector auth issue (works fine in Snowsight/browser, fails from the Python connector -- likely a network policy; see `docs/tasks/task2_data_exploration_and_enhancement.md`)
- [x] Task 3 — NoSQL (MongoDB) schema design — **verified**: `docker compose up -d mongo` + `python -m mongo.init_collections` run successfully, all three collections (`annotations`, `supplementary_sources`, `user_preferences`) created with validators and indexes; independent of the Task 2 blocker
- [ ] Task 4 — API development (FastAPI) — not started
- [ ] Task 5 — Interactive visualization (Dash/Plotly) + annotations bonus — not started
- [ ] Task 6 — Forecasting + clustering bonus — not started
- [x] Task 7 — Snowflake performance optimization — self-contained SQL (clustering key, materialized view, before/after profiling), runnable directly in Snowsight, independent of the Task 2 blocker
- [ ] Task 8 — API caching — not started
- [x] Task 9 — Pattern recognition (MATCH_RECOGNIZE) — wave detection + surge detection queries, runnable directly in Snowsight, independent of the Task 2 blocker
- [ ] Task 10 — GitHub repo + README + deployment docs — partially in place (per-task docs, docker-compose.yml started); full deployment README pending
- [ ] Final report (PDF/Word) with insights — not started
