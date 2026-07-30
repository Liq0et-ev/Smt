"""Task 4: FastAPI backend.

Two data sources, one API: Snowflake (structured COVID data, Task 2's
Gold layer) and MongoDB (annotations/comments, Task 3), plus on-the-fly
SQL processing (per-country wave detection, Task 9's MATCH_RECOGNIZE
pattern run live rather than pre-computed).

Run locally:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
Then open http://localhost:8000/docs for interactive Swagger UI.
"""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import annotations, countries

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(
    title="COVID-19 Data Platform API",
    description=(
        "Queries the Snowflake Gold layer (cases, deaths, vaccinations, "
        "demographics) and MongoDB (annotations) for the dashboard (Task 5) "
        "and any other client."
    ),
    version="1.0.0",
)

# Dashboard (Task 5) runs as a separate process/container and calls this
# API over HTTP -- needs CORS open for that. Fine to leave permissive for
# a capstone project talking to its own dashboard, not a public API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(countries.router)
app.include_router(annotations.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "covid-19-data-platform-api"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", 8000)),
        reload=True,
    )
