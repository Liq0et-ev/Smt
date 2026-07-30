"""Task 5: thin HTTP client the dashboard uses to talk to the FastAPI
backend (Task 4). The dashboard never queries Snowflake or MongoDB
directly -- every data access goes through the API, matching the
architecture diagram in the README."""
import os

import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
TIMEOUT = 60


def get_countries() -> list[dict]:
    resp = requests.get(f"{API_BASE_URL}/countries", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_daily(iso_code: str, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    resp = requests.get(f"{API_BASE_URL}/countries/{iso_code}/daily", params=params, timeout=TIMEOUT)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json()


def get_summary(iso_code: str) -> dict | None:
    resp = requests.get(f"{API_BASE_URL}/countries/{iso_code}/summary", timeout=TIMEOUT)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def get_cross_check(iso_code: str) -> list[dict]:
    resp = requests.get(f"{API_BASE_URL}/countries/{iso_code}/cross-check", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_waves(iso_code: str) -> list[dict]:
    resp = requests.get(f"{API_BASE_URL}/countries/{iso_code}/waves", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_annotations(iso_code: str, metric: str | None = None) -> list[dict]:
    params = {"metric": metric} if metric else {}
    resp = requests.get(
        f"{API_BASE_URL}/countries/{iso_code}/annotations", params=params, timeout=TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


def create_annotation(iso_code: str, metric: str, comment: str) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/countries/{iso_code}/annotations",
        json={"metric": metric, "comment": comment},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
