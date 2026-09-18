"""Fetch Yahoo Finance daily FX and equity prices into data/raw."""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
FOREX_OUTPUT = ROOT / "data" / "raw" / "forex" / "chf-usd.csv"
PRICE_OUTPUT = ROOT / "data" / "raw" / "prices"
SYMBOLS = {
    "nke": "NKE",
    "deck": "DECK",
    "onon": "ONON",
}
USER_AGENT = "Mozilla/5.0 (compatible; EquityResearchDataFetcher/1.0)"
CHART_HOSTS = ("query2.finance.yahoo.com", "query1.finance.yahoo.com")
RETRIES = 3


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Expected YYYY-MM-DD, got {value!r}") from exc


def epoch_seconds(value: date) -> int:
    return int(datetime(value.year, value.month, value.day, tzinfo=timezone.utc).timestamp())


def fetch_chart(symbol: str, start: date, end: date) -> dict:
    # Yahoo's period2 is exclusive, so include the requested end date by using
    # the following midnight as the upper bound.
    params = urlencode({
        "period1": epoch_seconds(start),
        "period2": epoch_seconds(end + timedelta(days=1)),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    })
    errors = []
    for host in CHART_HOSTS:
        url = f"https://{host}/v8/finance/chart/{quote(symbol, safe='=')}?{params}"
        for attempt in range(RETRIES):
            request = Request(url, headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            })
            try:
                with urlopen(request, timeout=45) as response:
                    payload = json.load(response)
                result = payload.get("chart", {}).get("result")
                if not result:
                    raise RuntimeError(f"Yahoo returned no chart result for {symbol}")
                return result[0]
            except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
                errors.append(f"{host} attempt {attempt + 1}: {exc}")
                if attempt < RETRIES - 1:
                    time.sleep(2 ** attempt)
    raise RuntimeError("Yahoo Finance request failed:\n" + "\n".join(errors))


def chart_rows(chart: dict, symbol: str) -> list[dict]:
    timestamps = chart.get("timestamp") or []
    quotes = (chart.get("indicators", {}).get("quote") or [{}])[0]
    adjusted = (chart.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose", [])
    rows = []
    for index, timestamp in enumerate(timestamps):
        row = {
            "date": datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat(),
            "open": quotes.get("open", [None] * len(timestamps))[index],
            "high": quotes.get("high", [None] * len(timestamps))[index],
            "low": quotes.get("low", [None] * len(timestamps))[index],
            "close": quotes.get("close", [None] * len(timestamps))[index],
            "adj_close": adjusted[index] if index < len(adjusted) else None,
            "volume": quotes.get("volume", [None] * len(timestamps))[index],
        }
        if symbol != "CHFUSD=X":
            row["ticker"] = symbol
        rows.append(row)
    return rows


def write_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"Yahoo returned no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["date", "open", "high", "low", "close", "adj_close", "volume"]
    if "ticker" in rows[0]:
        fields.append("ticker")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fetch_and_write(label: str, symbol: str, start: date, end: date, path: Path) -> None:
    chart = fetch_chart(symbol, start, end)
    rows = chart_rows(chart, symbol)
    write_rows(path, rows)
    print(f"{label}: {symbol} -> {path} ({len(rows):,} rows)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=parse_date, default=date(2019, 1, 1),
                        help="First date to request, inclusive (default: 2019-01-01)")
    parser.add_argument("--end", type=parse_date, default=date.today(),
                        help="Last date to request, inclusive (default: today)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.end < args.start:
        raise SystemExit("--end must be on or after --start")

    requested = [("FX", "CHFUSD=X", FOREX_OUTPUT)]
    for filename, symbol in SYMBOLS.items():
        requested.append(("Price", symbol, PRICE_OUTPUT / f"{filename}.csv"))

    # Fetch every series before writing any output, so a partial run cannot be
    # mistaken for a complete market-data refresh.
    fetched = []
    for label, symbol, path in requested:
        chart = fetch_chart(symbol, args.start, args.end)
        fetched.append((label, symbol, path, chart_rows(chart, symbol)))

    for label, symbol, path, rows in fetched:
        write_rows(path, rows)
        print(f"{label}: {symbol} -> {path} ({len(rows):,} rows)")


if __name__ == "__main__":
    main()
