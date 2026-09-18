"""Build filing-linked DCF actuals from SEC filings converted by sec2md."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILINGS = ROOT / "data" / "raw" / "sec_filings"
OUT = ROOT / "data" / "raw" / "dcf_inputs"
DEFAULT_SCALE = {"NKE": 1_000_000, "DECK": 1_000, "ONON": 1_000_000, "FL": 1_000_000}
CURRENCY = {"NKE": "USD", "DECK": "USD", "ONON": "CHF", "FL": "USD"}

ALIASES = {
    "shares": {
        "class_a_shares_outstanding": [r"^class a shares outstanding$"],
        "class_b_shares_outstanding": [r"^class b shares outstanding$"],
    },
    "income": {
        "revenue": [r"^revenues$", r"^net sales"],
        "cost_of_revenue": [r"^cost of sales", r"^cost of goods sold"],
        "gross_profit": [r"^gross profit$"],
        "selling_general_admin": [r"^total selling and administrative expense$", r"^selling, general and administrative expenses", r"^selling and administrative expenses"],
        "operating_income": [r"^income from operations", r"^operating result$"],
        "pretax_income": [r"^income before income taxes", r"^income before taxes", r"^income / \(loss\) before taxes"],
        "income_tax_expense": [r"^income tax expense", r"^income tax benefit / \(expense\)"],
        "net_income": [r"^net income(?: / \(loss\))?$"],
        "weighted_average_basic_shares": [r"^basic$"],
        "weighted_average_diluted_shares": [r"^diluted$"],
    },
    "balance": {
        "cash_and_equivalents": [r"^cash and equivalents$", r"^cash and cash equivalents$"],
        "short_term_investments": [r"^short-term investments$", r"^other current financial assets$"],
        "accounts_receivable": [r"^accounts receivable, net$", r"^trade accounts receivable, net", r"^trade receivables$"],
        "inventory": [r"^inventories$"],
        "accounts_payable": [r"^accounts payable$", r"^trade accounts payable$", r"^trade payables$"],
        "other_current_assets": [r"^prepaid expenses and other current assets$", r"^other current operating assets$", r"^other current assets$"],
        "other_current_liabilities": [r"^accrued liabilities$", r"^other accrued expenses$", r"^other current operating liabilities$"],
        "current_assets": [r"^total current assets$", r"^current assets$"],
        "current_liabilities": [r"^total current liabilities$", r"^current liabilities$"],
        "current_debt": [r"^current portion of long-term debt$", r"^short-term borrowings$"],
        "noncurrent_debt": [r"^long-term debt$", r"^non-current borrowings$"],
        "current_lease_liabilities": [r"^current portion of operating lease liabilities$", r"^current lease liabilities$", r"^operating lease liabilities, current$"],
        "noncurrent_lease_liabilities": [r"^operating lease liabilities$", r"^non-current lease liabilities$", r"^operating lease liabilities, noncurrent$"],
    },
    "cash_flow": {
        "cash_from_operations": [r"^cash provided \(used\) by operations$", r"^net cash provided by operating activities$", r"^cash inflow from operating activities$", r"^net cash provided by \(used in\) operating activities$"],
        "capital_expenditures": [r"^additions to property, plant and equipment$", r"^purchases of property and equipment$", r"^purchase of property, plant and equipment$"],
        "depreciation_amortization": [r"^depreciation and amortization$", r"^depreciation, amortization, and accretion$"],
        "stock_based_compensation": [r"^stock-based compensation$", r"^share-based compensation$"],
        "dividends_paid": [r"^dividends\s*[—-]\s*common and preferred$", r"^cash dividends paid$"],
        "interest_paid": [r"^interest paid$", r"^interest, net of capitalized interest$"],
        "change_in_working_capital": [r"^change in working capital$"],
    },
}


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def front_matter(markdown: str) -> dict[str, str]:
    if not markdown.startswith("---\n"):
        raise ValueError("Expected SEC filing front matter")
    return dict(line.split(": ", 1) for line in markdown.split("---", 2)[1].strip().splitlines() if ": " in line)


def filing_sources() -> list[dict]:
    sources = []
    for path in sorted(FILINGS.glob("*/*.md")):
        markdown = path.read_text(encoding="utf-8")
        metadata = front_matter(markdown)
        if metadata["ticker"] not in DEFAULT_SCALE:
            continue
        sources.append({"ticker": metadata["ticker"], "form": metadata["form"],
                        "period_end": metadata["report_date"], "filing_date": metadata["filing_date"],
                        "source_url": metadata["source"], "path": path, "markdown": markdown})
    return sources


def statement_heading(ticker: str, line: str) -> str | None:
    if line.startswith("|"):
        return None
    label = re.sub(r"[*_]+", "", line).strip().lower()
    if not "consolidated" in label or len(label) > 100:
        return None
    if "balance sheet" in label:
        return "balance"
    if "cash flow" in label:
        return "cash_flow"
    if "comprehensive income" in label and ticker != "DECK":
        return None
    if any(x in label for x in ["statements of income", "statement of income", "statements of operations", "statements of comprehensive income"]):
        return "income"
    return None


def amount(cell: str) -> float | None:
    raw = cell.strip().replace("$", "").replace("CHF", "").replace(",", "")
    if not raw or raw in {"—", "-", "–"} or "%" in raw:
        return None
    negative = "(" in raw and ")" in raw
    raw = raw.replace("(", "").replace(")", "").strip()
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", raw):
        return None
    value = float(raw)
    return -value if negative else value


def table_scale(unit_header: str, ticker: str) -> int:
    """Return the unit multiplier declared by the individual statement table.

    Most issuers use one unit consistently, but ONON's first 20-F reported CHF
    in thousands and later filings report CHF in millions. A ticker-level scale
    silently inflated the 2019 rows by 1,000x, so the table header is the source
    of truth and the issuer default is only a fallback for legacy headers.
    """
    normalized = re.sub(r"\s+", " ", unit_header.lower())
    if "thousand" in normalized:
        return 1_000
    if "million" in normalized:
        return 1_000_000
    return DEFAULT_SCALE[ticker]


def header_periods(headers: list[str], source: dict, kind: str) -> list[tuple[str, str] | None]:
    periods = [None] * len(headers)
    current_duration = "annual" if source["form"] in {"10-K", "20-F"} else "interim"
    for i, header in enumerate(headers[1:], start=1):
        lower = header.lower()
        if "three-month" in lower or "three months" in lower:
            current_duration = "3_months"
        elif "six-month" in lower or "six months" in lower:
            current_duration = "6_months"
        elif "year ended" in lower or "years ended" in lower:
            current_duration = "annual"
        years = re.findall(r"20\d{2}", header)
        if not years:
            continue
        year = years[-1]
        end = f"{year}-{source['period_end'][5:]}"
        if kind == "balance":
            slash_date = re.search(r"\b\d{1,2}/\d{1,2}/20\d{2}\b", header)
            named_date = re.search(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d{2}\b", header, re.I)
            if slash_date:
                end = datetime.strptime(slash_date.group(), "%m/%d/%Y").date().isoformat()
            elif named_date:
                text = named_date.group().replace(",", "")
                end = datetime.strptime(text, "%B %d %Y").date().isoformat()
        periods[i] = (end, "instant" if kind == "balance" else current_duration)
    return periods


def statement_rows(source: dict) -> list[dict]:
    lines = source["markdown"].splitlines()
    ticker = source["ticker"]
    rows = []
    pending = None
    for i, line in enumerate(lines):
        heading = statement_heading(ticker, line)
        if heading:
            pending = heading
            continue
        if not pending or not line.startswith("|") or i + 1 >= len(lines) or not lines[i + 1].startswith("| ---"):
            continue
        headers = [cell.strip() for cell in line.strip().strip("|").split("|")]
        scale = table_scale(headers[0], ticker)
        periods = header_periods(headers, source, pending)
        if sum(period is not None for period in periods) < 1:
            continue
        row_index = i + 2
        occurrences = {}
        while row_index < len(lines) and lines[row_index].startswith("|"):
            cells = [cell.strip() for cell in lines[row_index].strip().strip("|").split("|")]
            if cells and len(cells) == len(headers):
                label = cells[0]
                occurrences[label] = occurrences.get(label, 0) + 1
                share_match = re.search(r"^Class ([AB])(?: convertible)?\s*[—-]\s*([\d,]+) and ([\d,]+) shares outstanding", label)
                if ticker == "NKE" and pending == "balance" and share_match:
                    share_values = [float(share_match.group(2).replace(",", "")),
                                    float(share_match.group(3).replace(",", ""))]
                    for col, period in enumerate(periods[1:3], start=1):
                        if period is not None:
                            rows.append({"ticker": ticker, "statement": "shares", "period_end": period[0],
                                         "duration": "instant", "line_item": f"Class {share_match.group(1)} shares outstanding",
                                         "row_occurrence": 1, "reported_value": share_values[col - 1],
                                         "reported_scale": scale, "currency": "shares",
                                         "source_column": headers[col], "source_line": row_index + 1,
                                         "form": source["form"], "filing_date": source["filing_date"],
                                         "source_url": source["source_url"]})
                for col, period in enumerate(periods):
                    if period is None:
                        continue
                    value = amount(cells[col])
                    if value is None:
                        continue
                    rows.append({"ticker": ticker, "statement": pending, "period_end": period[0],
                                 "duration": period[1], "line_item": label, "reported_value": value,
                                 "row_occurrence": occurrences[label],
                                 "reported_scale": scale, "currency": CURRENCY[ticker],
                                 "source_column": headers[col], "source_line": row_index + 1,
                                 "form": source["form"], "filing_date": source["filing_date"],
                                 "source_url": source["source_url"]})
            row_index += 1
        pending = None
    return rows


def mapped_metric(row: dict) -> str | None:
    label = re.sub(r"\s+", " ", row["line_item"].lower()).strip()
    for metric, aliases in ALIASES[row["statement"]].items():
        if any(re.search(pattern, label) for pattern in aliases):
            if metric.startswith("weighted_average") and row["ticker"] != "NKE":
                continue
            if metric.startswith("weighted_average") and row["statement"] == "income":
                # NIKE has both EPS and weighted-share Basic/Diluted rows. Only
                # values in the share-count range represent diluted shares.
                if abs(row["reported_value"]) < 100:
                    continue
            return metric
    return None


def build_rows() -> tuple[list[dict], list[dict], list[dict]]:
    sources = filing_sources()
    all_rows = [row for source in sources for row in statement_rows(source)]
    # Comparative columns recur in annual filings. Retain the most recently
    # filed version of each fiscal-period statement line.
    all_rows.sort(key=lambda row: row["filing_date"], reverse=True)
    unique = {}
    for row in all_rows:
        key = (row["ticker"], row["statement"], row["period_end"], row["duration"], row["line_item"], row["row_occurrence"])
        unique.setdefault(key, row)
    statement_data = sorted(unique.values(), key=lambda row: (row["ticker"], row["period_end"], row["statement"], row["line_item"]))
    metrics = {}
    for row in statement_data:
        metric = mapped_metric(row)
        if not metric:
            continue
        key = (row["ticker"], row["period_end"], row["duration"], metric)
        if key not in metrics or row["filing_date"] > metrics[key]["filing_date"]:
            metrics[key] = {"ticker": row["ticker"], "period_end": row["period_end"],
                            "duration": row["duration"], "metric": metric,
                            "value": abs(row["reported_value"]) * row["reported_scale"] if metric in {"capital_expenditures", "cost_of_revenue", "income_tax_expense", "selling_general_admin", "dividends_paid", "interest_paid"} else row["reported_value"] * row["reported_scale"],
                            "currency": row["currency"] if not metric.startswith("weighted_average") else "shares",
                            "line_item": row["line_item"], "source_column": row["source_column"],
                            "source_line": row["source_line"], "form": row["form"],
                            "filing_date": row["filing_date"], "source_url": row["source_url"]}
    source_index = [{"ticker": s["ticker"], "form": s["form"], "period_end": s["period_end"],
                     "filing_date": s["filing_date"], "source_url": s["source_url"]} for s in sources]
    return statement_data, sorted(metrics.values(), key=lambda r: (r["ticker"], r["period_end"], r["metric"])), source_index


def main() -> None:
    statements, metrics, sources = build_rows()
    write_csv(OUT / "filing_statement_rows.csv",
              ["ticker", "statement", "period_end", "duration", "line_item", "row_occurrence", "reported_value",
               "reported_scale", "currency", "source_column", "source_line", "form", "filing_date", "source_url"], statements)
    write_csv(OUT / "financial_facts.csv",
              ["ticker", "period_end", "duration", "metric", "value", "currency", "line_item",
               "source_column", "source_line", "form", "filing_date", "source_url"], metrics)
    write_csv(OUT / "filing_index.csv",
              ["ticker", "form", "period_end", "filing_date", "source_url"], sources)
    print(f"sec2md: {len(statements)} statement cells, {len(metrics)} mapped DCF facts, {len(sources)} filings")


if __name__ == "__main__":
    main()
