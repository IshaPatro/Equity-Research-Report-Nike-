"""Build the canonical 2019-2026 SEC Markdown archive with sec2md."""

from __future__ import annotations

from pathlib import Path

import requests
from sec2md import convert_to_markdown


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "raw" / "sec_filings"
USER_AGENT = "Nike Equity Research research@example.com"
START_YEAR = 2019
END_YEAR = 2026

COMPANIES = {
    "NKE": {"cik": "0000320187", "forms": {"10-K"}},
    "DECK": {"cik": "0000910521", "forms": {"10-K"}},
    "ONON": {"cik": "0001858985", "forms": {"20-F"}},
    "FL": {"cik": "0000850209", "forms": {"10-K"}},
}

# These reports support the LTM DCF roll-forward and live beside annual reports.
INTERIM_FILINGS = [
    {
        "ticker": "DECK", "cik": "0000910521", "form": "10-Q",
        "reportDate": "2026-06-30", "filingDate": "2026-07-30",
        "accessionNumber": "0000910521-26-000022",
        "url": "https://www.sec.gov/Archives/edgar/data/910521/000091052126000022/deck-20260630.htm",
    },
    {
        "ticker": "ONON", "cik": "0001858985", "form": "6-K",
        "reportDate": "2026-06-30", "filingDate": "2026-08-11",
        "accessionNumber": "0001858985-26-000018",
        "url": "https://www.sec.gov/Archives/edgar/data/1858985/000185898526000018/onholdingag-20260630_d2.htm",
    },
]


def annual_filings(cik: str, forms: set[str]) -> list[dict[str, str]]:
    """Return annual filings with report dates from 2019 through 2026."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    recent = response.json()["filings"]["recent"]
    filings = []
    for index, form in enumerate(recent["form"]):
        report_date = recent["reportDate"][index]
        if form in forms and START_YEAR <= int(report_date[:4]) <= END_YEAR:
            filings.append({key: recent[key][index] for key in recent})
    return sorted(filings, key=lambda filing: filing["reportDate"])


def filing_url(cik: str, filing: dict[str, str]) -> str:
    accession = filing["accessionNumber"].replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{accession}/{filing['primaryDocument']}"
    )


def target_path(ticker: str, filing: dict[str, str]) -> Path:
    form = filing["form"].replace("/", "-")
    return OUTPUT_DIR / ticker / (
        f"{form}_{filing['reportDate']}_filed_{filing['filingDate']}.md"
    )


def write_filing(ticker: str, cik: str, filing: dict[str, str], url: str) -> Path:
    target = target_path(ticker, filing)
    if target.exists():
        return target
    markdown = convert_to_markdown(url, user_agent=USER_AGENT)
    if not markdown.strip():
        raise ValueError(f"sec2md returned an empty filing for {url}")
    header = "\n".join([
        "---", f"ticker: {ticker}", f"cik: '{cik}'", f"form: {filing['form']}",
        f"report_date: {filing['reportDate']}", f"filing_date: {filing['filingDate']}",
        f"accession_number: {filing['accessionNumber']}", f"source: {url}",
        "converter: sec2md", "---", "",
    ])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(header + markdown, encoding="utf-8")
    return target


def main() -> None:
    written = []
    for ticker, company in COMPANIES.items():
        filings = annual_filings(company["cik"], company["forms"])
        for filing in filings:
            written.append(write_filing(
                ticker, company["cik"], filing, filing_url(company["cik"], filing)
            ))
        print(f"{ticker}: {len(filings)} annual filing(s)")

    for filing in INTERIM_FILINGS:
        written.append(write_filing(
            filing["ticker"], filing["cik"], filing, filing["url"]
        ))
    print(f"Canonical archive: {len(written)} Markdown filing(s) in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
