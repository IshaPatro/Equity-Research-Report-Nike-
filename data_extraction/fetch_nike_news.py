"""Fetch Nike-specific news into the fixed equity-research window."""

from __future__ import annotations

import csv
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "news" / "nike_news.csv"
ANALYSIS_START = date(2019, 1, 1)
ANALYSIS_CUTOFF = date(2026, 9, 15)
SEARCH_URL = "https://serpapi.com/search.json"
SOURCE_URL = "https://serpapi.com/google-news-api"


def api_keys() -> list[str]:
    load_dotenv(ROOT / ".env")
    keys = [value for name in ("SERP_API", *(f"SERP_API_{index}" for index in range(1, 7)))
            if (value := os.getenv(name))]
    if keys:
        return keys
    raise RuntimeError("Set SERP_API in .env before fetching Nike news")


def published_at(item: dict) -> datetime | None:
    value = item.get("iso_date") or item.get("published_at")
    if not value:
        return None
    if value.endswith(" UTC"):
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S UTC").replace(
            tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def next_month(start: date) -> date:
    return date(start.year + (start.month == 12), start.month % 12 + 1, 1)


def month_starts() -> list[date]:
    starts = []
    current = ANALYSIS_START.replace(day=1)
    while current <= ANALYSIS_CUTOFF:
        starts.append(current)
        current = next_month(current)
    return starts


def search_month(month_start: date, key: str) -> tuple[date, list[dict]]:
    month_end = min(next_month(month_start), ANALYSIS_CUTOFF + timedelta(days=1))
    response = requests.get(
        SEARCH_URL,
        params={
            "engine": "google",
            "tbm": "nws",
            "q": f"Nike NKE after:{month_start.isoformat()} before:{month_end.isoformat()}",
            "gl": "us",
            "hl": "en",
            "num": 100,
            "api_key": key,
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    if message := payload.get("error"):
        raise RuntimeError(f"News provider error for {month_start:%Y-%m}: {message}")
    return month_start, payload.get("news_results", [])


def main() -> None:
    keys = api_keys()
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    starts = month_starts()
    with ThreadPoolExecutor(max_workers=len(keys)) as executor:
        searches = executor.map(
            lambda pair: search_month(pair[1], keys[pair[0] % len(keys)]),
            enumerate(starts),
        )
        monthly_results = sorted(searches, key=lambda result: result[0])

    for month_start, results in monthly_results:
        for item in results:
            timestamp = published_at(item)
            heading = item.get("title", "")
            link = item.get("link", "")
            if (not timestamp or not heading or not link or link in seen or
                    "nike" not in heading.lower() or
                    not ANALYSIS_START <= timestamp.date() <= ANALYSIS_CUTOFF):
                continue
            seen.add(link)
            rows.append({
                "date": timestamp.date().isoformat(),
                "time": timestamp.strftime("%H:%M:%S UTC"),
                "source_url": link,
                "heading": heading,
                "description": item.get("snippet", ""),
            })
        print(f"Searched {month_start:%Y-%m}")

    rows.sort(key=lambda row: (row["date"], row["time"], row["source_url"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    columns = ["date", "time", "source_url", "heading", "description"]
    with OUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    dates = [row["date"] for row in rows]
    print(f"Wrote {len(rows)} Nike news items to {OUT}")
    print(f"Coverage after filter: {min(dates, default='none')} to "
          f"{max(dates, default='none')}; research window: {ANALYSIS_START} to {ANALYSIS_CUTOFF}")


if __name__ == "__main__":
    main()
