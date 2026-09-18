"""Extract non-filing market inputs for a Nike DCF."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "dcf_inputs"
TREASURY_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?field_tdr_date_value=2026&type=daily_treasury_yield_curve"
ERP_URL = "https://pages.stern.nyu.edu/adamodar/New_Home_Page/home.htm"
BETA_URL = "https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/Betas.html"
PEERS_URL = "https://companiesmarketcap.com/footwear/largest-companies-by-market-cap/"


def page(url: str) -> BeautifulSoup:
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def treasury_input() -> dict:
    soup = page(TREASURY_URL)
    table = next(t for t in soup.find_all("table") if "10 Yr" in t.get_text() or "10 YR" in t.get_text())
    headings = [cell.get_text(" ", strip=True).lower() for cell in table.find("tr").find_all(["td", "th"])]
    index = next(i for i, name in enumerate(headings) if name in {"10 yr", "10 year"})
    for row in table.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        if cells and cells[0] == "09/15/2026":
            return {"input": "risk_free_rate_10y_usd", "value": f"{float(cells[index]) / 100:.6f}",
                    "unit": "fraction", "observation_date": "2026-09-15", "source_url": TREASURY_URL,
                    "note": "Nominal 10-year Treasury par yield"}
    raise RuntimeError("No 2026-09-15 10-year Treasury rate")


def erp_input() -> dict:
    text = page(ERP_URL).get_text(" ", strip=True)
    match = re.search(r"Implied ERP on September 1, 2026\s*=\s*([0-9]+)\.\s*([0-9]+)%", text, re.I)
    if not match:
        raise RuntimeError("No September 2026 implied equity risk premium")
    return {"input": "implied_us_equity_risk_premium", "value": f"{float(f'{match.group(1)}.{match.group(2)}') / 100:.6f}",
            "unit": "fraction", "observation_date": "2026-09-01", "source_url": ERP_URL,
            "note": "Trailing 12-month adjusted payout estimate"}


def shoe_beta_input() -> dict:
    soup = page(BETA_URL)
    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        if cells and cells[0] == "Shoe":
            return {"input": "shoe_industry_unlevered_beta", "value": cells[5], "unit": "beta",
                    "observation_date": "2026-01", "source_url": BETA_URL,
                    "note": f"Damodaran U.S. industry sample, {cells[1]} firms; relever for Nike's capital structure"}
    raise RuntimeError("No Shoe industry beta")


def existing_peer_snapshot() -> list[dict]:
    source_path = ROOT / "data" / "raw" / "companies_market_cap" / "companiesmarketcap.com - Largest footwear companies by market cap.csv"
    selected = {"NKE", "DECK", "ONON", "ADS.DE", "PUM.DE"}
    with source_path.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))
    return [{"company": row["Name"], "ticker": row["Symbol"],
             "market_cap_usd": row["marketcap"], "price_usd": row["price (USD)"],
             "observation_date": "", "source_url": PEERS_URL,
             "note": "Source CSV has no capture date; refresh before valuation"}
            for row in rows if row["Symbol"] in selected]


def main() -> None:
    write_csv(OUT / "wacc_market_inputs.csv",
              ["input", "value", "unit", "observation_date", "source_url", "note"],
              [treasury_input(), erp_input(), shoe_beta_input()])
    write_csv(OUT / "peer_market_snapshot.csv",
              ["company", "ticker", "market_cap_usd", "price_usd", "observation_date", "source_url", "note"],
              existing_peer_snapshot())
    print("Wrote dated WACC inputs and the existing undated peer market snapshot")


if __name__ == "__main__":
    main()
