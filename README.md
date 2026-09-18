# Equity Research Report

## Equity Research Dashboard

The static black-themed research dashboard is in [`docs/`](docs/index.html) and is ready for GitHub Pages using the repository's `/docs` publishing source. It presents the recommendation, DCF valuation, forecast, sensitivity analysis, distribution case study, risks, catalysts, and linked research sources in one responsive page. Its analytical figures are saved notebook outputs copied from `data/results`, so the notebooks remain the calculation and visualization source of truth. The bull scenario is green, the bear scenario is red, and the base scenario uses Nike yellow.

## Raw Data

Raw datasets are stored under `data/raw`. The project research window is **January 1, 2019 through September 15, 2026**. The supplied total footwear market-cap figure is **$173.43B**, an undated snapshot. Market prices and capitalization must be refreshed for the valuation date.

The single SEC archive is `data/raw/sec_filings`. It contains only Markdown reports, organized by ticker, covering available annual filings with report dates from 2019 through 2026 plus the two 2026 interim reports required for the DCF roll-forward. The archive includes NKE, DECK, ONON, and Foot Locker (FL). ONON has no annual SEC report before 2021, but its first 20-F filed in 2022 includes audited 2019-2021 comparative financial periods; a 2019 financial period must not be mistaken for a 2019 SEC filing. Foot Locker's latest available annual report covers the fiscal year ended February 1, 2025.

The extracted DCF inputs are in `data/raw/dcf_inputs`. `filing_statement_rows.csv` preserves reported income, balance-sheet, and cash-flow cells and their scale. `financial_facts.csv` maps DCF metrics into absolute units. Both include the SEC source URL and Markdown source line for each value.

Run the extraction scripts from the repository root:

```bash
python3 data_extraction/fetch_yahoo_market_data.py
python3 data_extraction/fetch_sec_filings.py
python3 data_extraction/extract_sec_statements.py
python3 data_extraction/extract_market_inputs.py
python3 data_extraction/fetch_nike_news.py
```

`fetch_yahoo_market_data.py` uses Yahoo Finance's chart endpoint with a default date range from January 1, 2019 through the run date. It saves the CHF/USD daily series from `CHFUSD=X` to `data/raw/forex/chf-usd.csv` and daily equity prices for Nike (`NKE`), Deckers (`DECK`), and On (`ONON`) under `data/raw/prices`. Override the range with `--start YYYY-MM-DD --end YYYY-MM-DD`; the end date is inclusive. The script preserves Yahoo's null observations, while downstream preprocessing removes unusable rows. Foot Locker is excluded because its former ticker is delisted and the case study uses Foot Locker only as retailer-side filing evidence.

SEC filings are converted and their financial statement data extracted only through `sec2md`. SEC submissions metadata identifies filings but does not supply financial values. ADDYY and PMMAF do not provide the required annual 10-K or 20-F series in SEC submissions.

## DCF Preprocessing

Run [the complete preprocessing notebook](data_extraction/preprocess_all.ipynb) after refreshing the raw inputs. The notebook deletes and recreates `data/preprocess` using only files under `data/raw`. Its unnumbered Markdown documents every transformation, formula, manual selection, and modelling limitation. It writes the native-currency schedules, separate USD schedules that translate ONON's CHF financials with dated CHF/USD observations, the cleaned FX ledger, market references, filing-derived case-study files, the prepared NKE/DECK/ONON adjusted-price ledger, and a preprocessing manifest. Validation is embedded in the notebook and stops execution on source-unit, provenance, duplicate-key, accounting-identity, period-selection, LTM, balance, FX, price-history, or case-study errors.

Historical actuals cover the three latest fiscal years per SEC-reporting company. LTM flows roll forward DECK and ONON using comparative interim periods; NKE uses its latest available full year. Native ONON schedules remain in CHF, while parallel USD schedules use the latest valid Yahoo Finance `CHFUSD=X` adjusted close on or before each reporting date. Operating working capital and FCFF are labelled proxies, not filing-reported cash flow or final forecast assumptions. The undated peer market snapshot is retained for reference but is not a current valuation quote.

## Nike DCF Model

Run [the DCF modelling notebook](research/model_nke_dcf.ipynb) after the preprocessing notebook. The rewritten notebook teaches the calculation in 68 small steps, each with a formula, purpose, matching code, and highlighted assumptions where applicable. It includes no case-study sections or interview questions. Install its dependencies with `python -m pip install -r data_extraction/requirements_dcf.txt`.

The model calculates bear/base/bull FCFF forecasts, WACC, a perpetual-growth terminal value with reinvestment tied to growth and ROIC, and the enterprise-to-equity bridge. It then applies a separately reported sentiment overlay capped at 2% of fundamental value. The notebook uses the shared black-background palette in `ui/constants.py` and saves each historical, forecast, cash-generation, valuation, and sensitivity chart independently. Its overall price-target chart uses the trailing 12 months of daily NKE adjusted closes from `data/raw/prices/nke.csv`, then displays the bear/base/bull DCF values as Low/Average/High at a one-year visual horizon. Those dashed paths are not a forecast of the price route. The base adjusted DCF is the overall target; Buy requires at least 15% upside, Sell requires at least 15% downside, and values between those thresholds are Hold. These are explicit analyst assumptions, not external consensus ratings. Green and red identify positive/Buy/bull and negative/Sell/bear outcomes; the base scenario remains Nike yellow. The Nike logo appears once in the dashboard label rather than across every figure. Results from this version are written to `data/results/dcf_learning` when the notebook runs. The older files directly under `data/results` belong to the previous model and are not outputs of this rewrite.

The five-column [Nike news file](data/raw/news/nike_news.csv) contains monthly search results within January 1, 2019 through September 15, 2026; it is not an exhaustive archive. The rewritten model scores headings and descriptions with VADER, removes repeated URLs/headings, averages by publisher domain and publication day, and weights the last 90 days with a 30-day half-life. It excludes articles published after September 15 at 4 p.m. New York time. The final price adjustment is `2% x weighted sentiment`, capped at plus/minus 2%, with zero adjustment below 10 publisher/day observations. These policy settings are uncalibrated analyst assumptions. Fundamental DCF values remain visible; there is no separate news-informed operating scenario. The older curated news-signal file remains available as research material.

## Running Distribution Case Study

[The Nike DTC and running-specialty case study](research/nike_running_distribution_case_study.md) tests the proposed retailer-exit and rival-share mechanism against SEC filing channel histories, Foot Locker disclosures, run-specialty research, and Nike's FY2026 recovery signals. The reproducible channel tables are in `data/preprocess/case_study`.

[The stepwise case-study notebook](research/nike_distribution_case_study.ipynb) teaches the analysis separately from the DCF. Each code cell is preceded by its formula or operation, why it matters, and any relevant assumption. It validates its inputs against the preprocessing manifest, distinguishes channel mix from channel dollars, shows the available Nike and Deckers wholesale history from 2019, leaves On's unavailable 2019-2020 observations blank, and uses Foot Locker as retailer-side evidence. It also compares normalized Yahoo Finance adjusted closes and marks selected distribution, leadership, retailer, and tariff events without treating nearby returns as causal effects. Its black-background charts use fixed-size company logos only inside series labels and fetch all colors from `ui/constants.py`. When run, it saves tables and charts to `data/results/distribution_case_study_learning`.

Previously created distribution research and charts remain available as separate reference material. They are excluded from the rewritten DCF notebook. Direct/DTC includes owned stores and e-commerce; wholesale partners may sell both online and offline.

The comparison price is Nike's September 15, 2026 close, not the undated peer market snapshot. Bear/base/bull forecast paths, forward debt spreads, and terminal growth are analyst assumptions. The FY2027 stub is linear, while the cash/debt bridge and shares come from Nike's May 2026 10-K. Its tariff-refund receivable was substantially collected after May 31, so the May cash and working-capital bridge may be stale at the September valuation date; no exact pro-forma adjustment is asserted. DCF values are conditional on these dates and assumptions and must be refreshed before use as a current target.

## Sources

- [SEC EDGAR filings](https://www.sec.gov/search-filings): annual and interim company reports.
- [SEC EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces): filing identification in the annual downloader.
- [sec2md](https://github.com/lucasastorian/sec2md): SEC filing-to-Markdown conversion.
- [Damodaran financial definitions](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/definitions.html): FCFF and operating-return definitions.
- [Damodaran terminal-growth derivation](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/AppldCF/derivn/ch12deriv.html): growth, reinvestment and return on capital in terminal value.
- [VADER original implementation](https://github.com/cjhutto/vaderSentiment): general-language sentiment lexicon and rules; version 3.3.2. It is not calibrated to Nike share-price returns.
- [CompaniesMarketCap footwear rankings](https://companiesmarketcap.com/footwear/largest-companies-by-market-cap/): existing peer market-cap and price CSV; capture date is not recorded.
- [U.S. Treasury daily rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?field_tdr_date_value=2026&type=daily_treasury_yield_curve): September 15, 2026 nominal 10-year yield.
- [Damodaran implied equity risk premium](https://pages.stern.nyu.edu/adamodar/New_Home_Page/home.htm): September 1, 2026 U.S. ERP.
- [Damodaran industry betas](https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/Betas.html): Shoe industry unlevered beta, January 2026 sample.
- [SerpApi news search results API](https://serpapi.com/news-results): monthly Nike news searches using credentials from `.env`, filtered to the January 1, 2019 through September 15, 2026 research window.
- [Yahoo Finance NKE historical chart](https://query1.finance.yahoo.com/v8/finance/chart/NKE?period1=1789430400%26period2=1789516800%26interval=1d): September 15, 2026 Nike closing price of $36.22 used for dated equity weights and upside comparison; it is not a second source for the existing peer market-cap CSV.
- [Yahoo Finance chart API](https://query2.finance.yahoo.com/v8/finance/chart/NKE): adjusted-close source used by `data_extraction/fetch_yahoo_market_data.py` for the NKE, DECK, and ONON price comparison; the same endpoint supplies `CHFUSD=X` for currency translation.
- [Nike FY2026 results release](https://investors.nike.com/investors/news-events-and-reports/investor-news/investor-news-details/2026/NIKE-Inc--Reports-Fiscal-2026-Fourth-Quarter-and-Full-Year-Results/default.aspx): tariff-recovery benefit and fourth-quarter channel performance.
- [Nike official Q4 FY2026 earnings-call transcript](https://s1.q4cdn.com/806093406/files/doc_financials/2026/q4/NIKE-Inc-Q4FY26-OFFICIAL-Transcript_-FINAL.pdf): early-FY2027 revenue outlook, margin actions, and tax-rate context.
- [Nike dividend announcement](https://investors.nike.com/investors/news-events-and-reports/investor-news/investor-news-details/2026/NIKE-Inc--Declares-0-41-Quarterly-Dividend-f1997578c/default.aspx): capital-allocation context, with no direct unlevered-FCFF change.
- [Nike Q1 FY2027 results-date announcement](https://investors.nike.com/investors/news-events-and-reports/investor-news/investor-news-details/2026/NIKE-Inc--Announces-First-Quarter-Fiscal-2027-Earnings-and-Conference-Call/default.aspx): October 1, 2026 reporting update trigger.
- [Nike 2020 Consumer Direct Acceleration announcement](https://investors.nike.com/investors/news-events-and-reports/investor-news/investor-news-details/2020/Nike-Announces-Senior-Leadership-Changes-to-Unlock-Future-Growth-Through-the-Consumer-Direct-Acceleration/default.aspx): owned, digital and strategic-partner strategy.
- [White House April 2, 2025 reciprocal-tariff announcement](https://www.whitehouse.gov/fact-sheets/2025/04/fact-sheet-president-donald-j-trump-declares-national-emergency-to-increase-our-competitive-edge-protect-our-sovereignty-and-strengthen-our-national-and-economic-security/): source for the Liberation Day event marker in the normalized equity-price chart.
- [Nike leadership appointment announcements](https://about.nike.com/en/newsroom/releases/nike-inc-announces-return-of-long-time-nike-veteran-elliott-hill-as-president-and-ceo): Hill's October 2024 CEO start; [Donahoe appointment](https://about.nike.com/en/newsroom/releases/board-member-john-donahoe-will-succeed-mark-parker-as-president-and-ceo-in-2020-parker-to-become-executive-chairman): January 2020 start.
- [Foot Locker FY2021 results](https://investors.footlocker-inc.com/news-releases/news-release-details/foot-locker-inc-reports-2021-fourth-quarter-and-full-year): vendor concentration and planned 2022 diversification.
- [Running Industry Association 2020 specialty report](https://runningindustry.org/resources/webinars/2020-run-specialty-market-report): pre/post-CDA brand positions; [2022 run-specialty report](https://runningindustry.org/news/ria-report-running-specialty-sees-solid-gains-in-2022): channel sales, doors and inventory-versus-sales observations; [supply-chain report](https://runningindustry.org/resources/research/supply-chain-report): industry-wide delivery context.
- [Deckers FY2023 results](https://ir.deckers.com/news-events/press-releases/detail/254/deckers-brands-reports-fourth-quarter-and-full-fiscal-year-2023-financial-results): context for the Deckers filing-derived channel series and its scope limitation.
- [Nike FY2026 Q1 results](https://investors.nike.com/investors/news-events-and-reports/investor-news/investor-news-details/2025/NIKE-Inc--Reports-Fiscal-2026-First-Quarter-Results/default.aspx): official Win Now wholesale and Running priorities.

The Nike DCF now includes explicit analyst forecast assumptions, a perpetual-growth terminal method, a dated comparison close, and an assumed forward borrowing spread. Before using a current target, update the news snapshot, company actuals, share price, debt valuation, share count, and WACC inputs; validate the working-capital proxy and scenario assumptions against the investment thesis. On Holding's financials are in CHF, so peer comparisons still need a dated currency conversion.
