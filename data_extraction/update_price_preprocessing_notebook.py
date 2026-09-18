"""Add reproducible equity-price preprocessing to preprocess_all.ipynb."""

from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "data_extraction/preprocess_all.ipynb"
TAG = "case-study-prices"


nb = nbformat.read(NOTEBOOK, as_version=4)
nb.cells = [cell for cell in nb.cells if TAG not in cell.get("metadata", {}).get("tags", [])]

sources = nb.cells[1].source
price_bullet = (
    "- `data/raw/prices` contains Yahoo Finance daily adjusted closes for NKE, DECK, "
    "and ONON.\n"
)
if price_bullet not in sources:
    marker = "- `data/raw/sec_filings` contains SEC filings converted to Markdown and is used for the channel case study.\n"
    nb.cells[1].source = sources.replace(marker, marker + price_bullet)

limitations = nb.cells[2].source
price_limit = (
    "- Equity-price comparisons use adjusted closes and normalize each ticker to its first "
    "available observation; ONON begins after its 2021 listing.\n"
)
if price_limit not in limitations:
    nb.cells[2].source = limitations.replace(
        "- Missing reported values remain missing. They are never silently replaced with zero.\n",
        price_limit + "- Missing reported values remain missing. They are never silently replaced with zero.\n",
    )

heading = nbformat.v4.new_markdown_cell(
    """## Build the daily equity-price history

The case-study price chart uses Yahoo Finance adjusted closes for Nike, Deckers, and On.
Adjusted close incorporates splits and distributions reported by the vendor, which is preferable
to raw close for a long comparison. Rows outside January 1, 2019 through September 15, 2026 are
removed. Each observation retains its provider URL.

No pre-listing On prices are created. Missing trading dates remain missing and are handled only
when the research notebook draws each observed series.""",
    metadata={"tags": [TAG]},
)

code = nbformat.v4.new_code_cell(
    """price_specs = {
    'Nike': ('NKE', raw / 'prices/nke.csv'),
    'Deckers': ('DECK', raw / 'prices/deck.csv'),
    'On': ('ONON', raw / 'prices/onon.csv'),
}
price_frames = []
for company, (ticker, path) in price_specs.items():
    frame = pd.read_csv(path)
    frame['date'] = pd.to_datetime(frame.date)
    frame = frame.loc[frame.date.between('2019-01-01', '2026-09-15')].copy()
    assert frame.ticker.eq(ticker).all()
    assert frame.adj_close.dropna().gt(0).all()
    frame['company'] = company
    frame['source_url'] = f'https://query2.finance.yahoo.com/v8/finance/chart/{ticker}'
    price_frames.append(frame[['date', 'company', 'ticker', 'adj_close', 'source_url']])

equity_prices = (pd.concat(price_frames, ignore_index=True)
                 .dropna(subset=['adj_close'])
                 .sort_values(['company', 'date'])
                 .reset_index(drop=True))
assert not equity_prices.duplicated(['ticker', 'date']).any()
assert equity_prices.groupby('ticker').adj_close.size().gt(1000).all()
assert equity_prices.loc[equity_prices.ticker.eq('ONON'), 'date'].min().year == 2021

price_case_path = case_out / 'equity_price_history.csv'
equity_prices.to_csv(price_case_path, index=False)
print(f'Wrote {price_case_path} ({len(equity_prices):,} rows)')""",
    metadata={"tags": [TAG]},
)

validation_index = next(
    i for i, cell in enumerate(nb.cells)
    if cell.cell_type == "markdown" and cell.source.startswith("## Validate the complete rebuilt directory")
)
nb.cells[validation_index:validation_index] = [heading, code]

for cell in nb.cells:
    if cell.cell_type == "code" and "expected_case_files = {" in cell.source:
        cell.source = cell.source.replace(
            '"foot_locker_nike_concentration.csv",\n}',
            '"foot_locker_nike_concentration.csv", "equity_price_history.csv",\n}',
        )
    if cell.cell_type == "code" and "for path in sorted(case_out.glob" in cell.source:
        old = """for path in sorted(case_out.glob(\"*.csv\")):
    manifest_rows.append({\"file\": str(path.relative_to(root)), \"rows\": len(pd.read_csv(path)),
                          \"source_scope\": \"raw SEC filing Markdown\", \"currency_policy\": \"reported currency\"})"""
        new = """for path in sorted(case_out.glob(\"*.csv\")):
    if path.name == 'equity_price_history.csv':
        source_scope, currency_policy = 'raw Yahoo Finance adjusted closes', 'USD per share'
    else:
        source_scope, currency_policy = 'raw SEC filing Markdown', 'reported currency'
    manifest_rows.append({\"file\": str(path.relative_to(root)), \"rows\": len(pd.read_csv(path)),
                          \"source_scope\": source_scope, \"currency_policy\": currency_policy})"""
        if old in cell.source:
            cell.source = cell.source.replace(old, new)
        elif new not in cell.source:
            raise RuntimeError("Could not locate case-study manifest loop")

for cell in nb.cells:
    if cell.cell_type == "code":
        cell.execution_count = None
        cell.outputs = []

nbformat.write(nb, NOTEBOOK)
print(f"Updated {NOTEBOOK.relative_to(ROOT)}")
