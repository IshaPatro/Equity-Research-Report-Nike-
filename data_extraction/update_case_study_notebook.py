"""Apply the current preprocessing and visual conventions to the case-study notebook."""

from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "research/nike_distribution_case_study.ipynb"
PRICE_SECTION_TAG = "price-event-section"


def set_source(cell, source):
    cell["source"] = source.strip() + "\n"


nb = nbformat.read(NOTEBOOK, as_version=4)
nb.cells = [
    cell for cell in nb.cells
    if PRICE_SECTION_TAG not in cell.get("metadata", {}).get("tags", [])
]

set_source(nb.cells[1], r"""
## Sources and boundaries

The three operating datasets were built from annual SEC reports already converted to Markdown
with `sec2md`. The preprocessing workflow preserves the original filing URL and Markdown line
for each value. A fourth prepared dataset contains Yahoo Finance adjusted closes. Every prepared
file is recorded in `preprocessing_manifest.csv`.

| Dataset | Scope | Key limitation |
|---|---|---|
| `nike_channel_history.csv` | Nike wholesale and Direct revenue, FY2019-FY2026; Nike Inc. gross margin | Direct combines owned stores and digital; gross margin covers all Nike Inc. |
| `peer_channel_history.csv` | Deckers filing-derived channel series in USD; On consolidated channels in CHF | Different currencies, fiscal calendars, product scopes and company maturity |
| `foot_locker_nike_concentration.csv` | Foot Locker purchases from Nike, 2019-2024 | Vendor purchases are not Nike sales, footwear share, sell-through or running-specialty share |
| `equity_price_history.csv` | Daily adjusted closes for NKE, DECK and ONON | On begins at its September 2021 listing; co-movement around events is not causal evidence |

Primary source: [SEC EDGAR](https://www.sec.gov/search-filings). Preprocessing notebook:
`data_extraction/preprocess_all.ipynb`. Supporting research and non-SEC sources:
`research/nike_running_distribution_case_study.md`. Daily adjusted closes come from the
[Yahoo Finance chart API](https://query2.finance.yahoo.com/v8/finance/chart/NKE); the prepared
price table preserves the corresponding ticker endpoint on every row.

The Consumer Direct Acceleration strategy was announced in 2020, emphasizing digital,
owned stores and selected strategic partners. The company sources are linked in the project
README and research memo. Strategy timing is context, not a randomized treatment date.

> **ASSUMPTION:** `Deckers` is the consistent display label for the Deckers filing-derived
> channel series. The series should not be interpreted as consolidated Deckers revenue.
""")

set_source(nb.cells[4], r"""
from pathlib import Path
import importlib
import json
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import to_rgb
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from IPython.display import display
""")

set_source(nb.cells[5], r"""
## Step 2: Set the project paths and visual system

**Formula or operation:** Locate the repository root, import the shared palette from
`ui/constants.py`, validate the logo files, and define reusable dark-chart helpers.

**Why?** Centralized colors keep every chart consistent. The supplied company logos make the
series easier to identify, while helper functions keep each logo at one fixed display size and
prevent charts from silently reverting to a white background or low-contrast labels.

> **ASSUMPTION:** Logos are recolored to their high-contrast series color for accessibility on
> a black background. Their geometry is unchanged, and logos appear only as part of labels.
""")

set_source(nb.cells[6], r"""
root = next(p for p in (Path.cwd(), *Path.cwd().parents)
            if (p / 'data/preprocess/preprocessing_manifest.csv').exists())
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import importlib
import ui.constants as chart_constants
importlib.reload(chart_constants)
from ui.constants import (BACKGROUND, PANEL_BACKGROUND, TEXT, MUTED_TEXT, GRID,
                          REFERENCE, FOOT_LOCKER, COMPANY_COLORS, CHANNEL_COLORS,
                          LOGO_FILES, LOGO_DISPLAY_PX, EVENT_COLORS)

preprocess_root = root / 'data/preprocess'
case_data = preprocess_root / 'case_study'
logo_dir = root / 'data/logo'
output = root / 'data/results/distribution_case_study_learning'
research_start = pd.Timestamp('2019-01-01')
research_cutoff = pd.Timestamp('2026-09-15')

for company, filename in LOGO_FILES.items():
    assert (logo_dir / filename).exists(), f'Missing {company} logo: {filename}'

plt.rcParams.update({
    'figure.facecolor': BACKGROUND,
    'savefig.facecolor': BACKGROUND,
    'axes.facecolor': PANEL_BACKGROUND,
    'axes.edgecolor': GRID,
    'axes.labelcolor': TEXT,
    'axes.titlecolor': TEXT,
    'xtick.color': MUTED_TEXT,
    'ytick.color': MUTED_TEXT,
    'text.color': TEXT,
    'legend.labelcolor': TEXT,
    'font.size': 10,
    'axes.titleweight': 'bold',
})


def style_axes(ax):
    ax.set_facecolor(PANEL_BACKGROUND)
    ax.grid(axis='y', color=GRID, linewidth=.8, alpha=.7)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.tick_params(colors=MUTED_TEXT)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)


def tinted_logo(company):
    image = plt.imread(logo_dir / LOGO_FILES[company])
    if image.shape[-1] == 3:
        alpha = np.ones(image.shape[:2], dtype=float)
    else:
        alpha = image[..., 3]
    visible = np.argwhere(alpha > .02)
    y0, x0 = visible.min(axis=0)
    y1, x1 = visible.max(axis=0) + 1
    alpha = alpha[y0:y1, x0:x1]
    stride = max(1, int(np.ceil(max(alpha.shape) / 160)))
    alpha = alpha[::stride, ::stride]
    tinted = np.zeros((*alpha.shape, 4), dtype=float)
    tinted[..., :3] = to_rgb(COMPANY_COLORS[company])
    tinted[..., 3] = alpha
    return tinted


def add_logo_label(ax, company, x, y, text=None, fontsize=9):
    logo_array = tinted_logo(company)
    zoom = LOGO_DISPLAY_PX / max(logo_array.shape[:2])
    image = OffsetImage(logo_array, zoom=zoom)
    logo = AnnotationBbox(image, (x, y), xycoords='axes fraction', frameon=False,
                          box_alignment=(0, .5), pad=0, zorder=10)
    ax.add_artist(logo)
    ax.annotate(text or company, xy=(x, y), xycoords='axes fraction',
                xytext=(LOGO_DISPLAY_PX + 8, 0), textcoords='offset points',
                color=COMPANY_COLORS[company], fontsize=fontsize,
                fontweight='bold', va='center', ha='left', zorder=10)


def add_company_labels(ax, companies, y=.94, fontsize=9):
    x_positions = np.linspace(.02, .48, len(companies))
    for x, company in zip(x_positions, companies):
        add_logo_label(ax, company, x=x, y=y, fontsize=fontsize)
""")

set_source(nb.cells[7], r"""
## Step 3: Load the manifest and four prepared datasets

**Formula or operation:** Confirm that the preprocessing manifest contains each case-study file,
then read the Nike, peer, Foot Locker and daily equity-price CSVs.

**Why?** The manifest check aligns this notebook with the current preprocessing workflow and
fails early if an input was renamed, omitted or moved.
""")

set_source(nb.cells[8], r"""
preprocessing_manifest = pd.read_csv(preprocess_root / 'preprocessing_manifest.csv')
required_inputs = {
    'data/preprocess/case_study/nike_channel_history.csv',
    'data/preprocess/case_study/peer_channel_history.csv',
    'data/preprocess/case_study/foot_locker_nike_concentration.csv',
    'data/preprocess/case_study/equity_price_history.csv',
}
assert required_inputs.issubset(set(preprocessing_manifest.file))

nike = pd.read_csv(case_data / 'nike_channel_history.csv')
peers = pd.read_csv(case_data / 'peer_channel_history.csv')
foot_locker = pd.read_csv(case_data / 'foot_locker_nike_concentration.csv')
prices = pd.read_csv(case_data / 'equity_price_history.csv')
nike['fiscal_year_end'] = pd.to_datetime(nike.fiscal_year_end)
peers['fiscal_year_end'] = pd.to_datetime(peers.fiscal_year_end)
prices['date'] = pd.to_datetime(prices.date)

# Normalize presentation labels without changing the filing-derived values.
peers.loc[peers.company.str.contains('Deckers', case=False), 'company'] = 'Deckers'
peers.loc[peers.company.eq('On Holding'), 'company'] = 'On'
peers.loc[peers.company.eq('Deckers'), 'scope'] = 'Deckers reported channel series'

display(pd.Series({'nike_rows': len(nike), 'peer_rows': len(peers),
                   'foot_locker_rows': len(foot_locker),
                   'price_rows': len(prices),
                   'manifest_rows': len(preprocessing_manifest)}))
""")

set_source(nb.cells[10], r"""
assert nike.fiscal_year.is_unique
assert not peers.duplicated(['company', 'fiscal_year']).any()
assert foot_locker.purchase_year.is_unique
assert not prices.duplicated(['ticker', 'date']).any()
assert nike.fiscal_year_end.between(research_start, research_cutoff).all()
assert peers.fiscal_year_end.between(research_start, research_cutoff).all()
assert foot_locker.purchase_year.between(2019, 2026).all()
assert prices.date.between(research_start, research_cutoff).all()
assert set(prices.company) == {'Nike', 'Deckers', 'On'}
assert prices.adj_close.gt(0).all()
""")

set_source(nb.cells[12], r"""
for frame in [nike, peers, foot_locker]:
    assert frame.source_url.str.startswith('https://www.sec.gov/Archives/').all()
assert prices.source_url.str.startswith(
    'https://query2.finance.yahoo.com/v8/finance/chart/').all()
assert nike[['wholesale_md_line', 'direct_md_line', 'gross_margin_md_line']].notna().all().all()
assert peers[['wholesale_md_line', 'direct_md_line']].notna().all().all()
assert foot_locker.md_line.notna().all()
""")

set_source(nb.cells[14], r"""
assert nike.currency.eq('USD').all() and nike.unit.eq('millions').all()
assert peers.unit.eq('millions').all()
assert (peers.loc[peers.company.eq('Deckers'), 'currency'] == 'USD').all()
assert (peers.loc[peers.company.eq('On'), 'currency'] == 'CHF').all()
assert np.allclose(peers.wholesale_revenue + peers.direct_revenue, peers.total_revenue,
                   atol=.11)
nike['global_brand_divisions'] = (nike.nike_brand_total - nike.nike_brand_wholesale
                                  - nike.nike_brand_direct)
assert nike.global_brand_divisions.ge(0).all()
display(nike[['fiscal_year', 'global_brand_divisions']])
""")

set_source(nb.cells[31], r"""
fig_nike, axes = plt.subplots(1, 2, figsize=(12, 4), layout='constrained')
axes[0].bar(nike.fiscal_year, nike.nike_brand_wholesale / 1000,
            label='Wholesale partners', color=CHANNEL_COLORS['Wholesale'])
axes[0].bar(nike.fiscal_year, nike.nike_brand_direct / 1000,
            bottom=nike.nike_brand_wholesale / 1000,
            label='Nike Direct', color=CHANNEL_COLORS['Direct'])
axes[0].set(title='Nike channel revenue', ylabel='USD billions', xlabel='Fiscal year')
axes[0].legend(frameon=False)
axes[1].plot(nike.fiscal_year, nike.direct_share_recalculated,
             marker='o', color=COMPANY_COLORS['Nike'], linewidth=2.5)
axes[1].set(title='Nike Direct share of two major channels',
            ylabel='Percent', xlabel='Fiscal year')
for ax in axes:
    style_axes(ax)
add_logo_label(axes[0], 'Nike', x=.80, y=.93)
add_logo_label(axes[1], 'Nike', x=.02, y=.93)
plt.show()
""")

set_source(nb.cells[33], r"""
## Step 15: Recalculate peer Direct share

**Formula or operation:** Peer Direct share = Direct revenue / total revenue x 100.

**Why?** Recalculation checks the prepared values and provides a comparable channel-mix definition within each peer's reported scope.

> **ASSUMPTION:** Similar formulas do not make company scopes identical. The Deckers series,
> On consolidated results and Nike channel data have different economic scopes.
""")

set_source(nb.cells[35], r"""
## Step 16: Build a common wholesale table

**Formula or operation:** Append Nike, Deckers and On wholesale observations without converting currencies.

**Why?** The combined table enables within-company normalization. The raw revenue column must never be summed across currencies.
""")

set_source(nb.cells[36], r"""
nike_wholesale = nike[['fiscal_year', 'nike_brand_wholesale']].rename(
    columns={'nike_brand_wholesale': 'wholesale_revenue'})
nike_wholesale['company'] = 'Nike'
nike_wholesale['currency'] = 'USD'
nike_wholesale['scope'] = 'Nike; all products'
wholesale = pd.concat([nike_wholesale, peers[['company', 'fiscal_year',
    'wholesale_revenue', 'currency', 'scope']]], ignore_index=True)
wholesale = wholesale.sort_values(['company', 'fiscal_year']).reset_index(drop=True)
assert not wholesale.duplicated(['company', 'fiscal_year']).any()
display(wholesale.head())
""")

set_source(nb.cells[37], r"""
## Step 17: Define the chart window and the common comparison window

**Formula or operation:** Keep FY2019-FY2024 for the chart, then retain FY2021-FY2024 as a
separate common window for like-period growth calculations.

**Why?** The chart should show the 2019 and 2020 history available for Nike and Deckers. On
does not report observations in this prepared dataset until 2021, so those two years remain
absent rather than being estimated. The common 2021-2024 table keeps the summary statistics
comparable across all three companies.

> **ASSUMPTION:** Fiscal years are labels. Nike ends in May, Deckers in March and On in December.
""")

set_source(nb.cells[38], r"""
wholesale_chart = wholesale.loc[wholesale.fiscal_year.between(2019, 2024)].copy()
comparison = wholesale.loc[wholesale.fiscal_year.between(2021, 2024)].copy()

chart_availability = wholesale_chart.groupby('company').fiscal_year.agg(['min', 'max', 'count'])
common_counts = comparison.groupby('company').fiscal_year.nunique()
assert chart_availability.loc['Nike', 'min'] == 2019
assert chart_availability.loc['Deckers', 'min'] == 2019
assert chart_availability.loc['On', 'min'] == 2021
assert common_counts.eq(4).all()
display(chart_availability.rename(columns={'min': 'first_year', 'max': 'last_year',
                                           'count': 'observations'}))
""")

set_source(nb.cells[39], r"""
## Step 18: Index wholesale revenue to each company's first available year

**Formula or operation:** Wholesale index = company wholesale revenue / first available
wholesale revenue x 100. Nike and Deckers use FY2019; On uses FY2021.

**Why?** This adds the requested 2019 and 2020 history without inventing On observations.
Within-company indexing cancels currency units and compares growth paths, not market share.

> **ASSUMPTION:** Mixed base years are clearly disclosed, so the chart is suitable for growth
> direction but not for comparing absolute company size or identical elapsed periods.
""")

set_source(nb.cells[40], r"""
first_observation = (wholesale_chart.sort_values('fiscal_year')
                     .groupby('company', as_index=False).first()
                     [['company', 'fiscal_year', 'wholesale_revenue']]
                     .rename(columns={'fiscal_year': 'base_year',
                                      'wholesale_revenue': 'base_wholesale_revenue'}))
wholesale_chart = wholesale_chart.merge(first_observation, on='company', validate='many_to_one')
wholesale_chart['wholesale_index_base'] = (
    100 * wholesale_chart.wholesale_revenue / wholesale_chart.base_wholesale_revenue)
assert np.allclose(wholesale_chart.loc[
    wholesale_chart.fiscal_year.eq(wholesale_chart.base_year), 'wholesale_index_base'], 100)
display(wholesale_chart[['company', 'fiscal_year', 'base_year', 'wholesale_index_base']])
""")

set_source(nb.cells[45], r"""
## Step 21: Plot indexed wholesale expansion from 2019

**Formula or operation:** Plot the within-company wholesale index across every available
observation from FY2019 through FY2024 and identify each series with a fixed-size logo label.

**Why?** The longer view shows that Deckers growth was already underway before 2021 while
leaving On's unavailable 2019-2020 values blank. Logos and high-contrast colors make the lines
distinguishable without changing the underlying data.
""")

set_source(nb.cells[46], r"""
fig_wholesale, ax = plt.subplots(figsize=(10, 5.5), layout='constrained')
for company, group in wholesale_chart.groupby('company'):
    group = group.sort_values('fiscal_year')
    ax.plot(group.fiscal_year, group.wholesale_index_base,
            marker='o', linewidth=2.7, color=COMPANY_COLORS[company])
ax.axhline(100, color=REFERENCE, linewidth=1)
ax.set(title='Wholesale revenue growth within each company',
       xlabel='Fiscal-year label', ylabel='Index: first available year = 100')
ax.set_xticks(range(2019, 2025))
ax.margins(x=.08, y=.12)
style_axes(ax)
add_company_labels(ax, ['Deckers', 'Nike', 'On'])
plt.show()
""")

set_source(nb.cells[47], r"""
## Step 22: Compare Direct-share trajectories

**Formula or operation:** Plot reported Direct share for Nike, Deckers and On within each scope.

**Why?** The chart tests whether competitors were exclusively wholesale-led. A rising peer
Direct share would show that wholesale growth and Direct investment can coexist.

> **ASSUMPTION:** Direct definitions and company scopes may differ in detail. The chart compares direction, not identical channel economics.
""")

set_source(nb.cells[48], r"""
direct_mix = pd.concat([
    nike[['fiscal_year', 'direct_share_recalculated']].assign(company='Nike').rename(
        columns={'direct_share_recalculated': 'direct_share_pct'}),
    peers[['company', 'fiscal_year', 'direct_share_recalculated']].rename(
        columns={'direct_share_recalculated': 'direct_share_pct'})
], ignore_index=True)
fig_direct, ax = plt.subplots(figsize=(10, 5.5), layout='constrained')
for company, group in direct_mix.groupby('company'):
    group = group.sort_values('fiscal_year')
    ax.plot(group.fiscal_year, group.direct_share_pct, marker='o',
            linewidth=2.5, color=COMPANY_COLORS[company])
ax.set(title='Company-operated channel share within reported scope',
       xlabel='Fiscal-year label', ylabel='Direct share (%)')
ax.margins(x=.08, y=.12)
style_axes(ax)
add_company_labels(ax, ['Deckers', 'Nike', 'On'])
plt.show()
""")

set_source(nb.cells[57], r"""
fig_fl, ax = plt.subplots(figsize=(8, 4), layout='constrained')
ax.plot(foot_locker.purchase_year, foot_locker[share_col], marker='o',
        linewidth=2.5, color=FOOT_LOCKER)
ax.set(title='Foot Locker purchases sourced from Nike',
       xlabel='Purchase year', ylabel='Share of merchandise purchases (%)', ylim=(0, 100))
style_axes(ax)
add_logo_label(ax, 'Nike', x=.02, y=.93, text='Nike supplier share')
plt.show()
""")

set_source(nb.cells[63], r"""
fig_alignment, axes = plt.subplots(1, 2, figsize=(11, 4), layout='constrained')
axes[0].plot(aligned.fiscal_year, aligned.direct_share_recalculated,
             marker='o', color=COMPANY_COLORS['Nike'], linewidth=2.5)
axes[0].set(title='Nike Direct mix', ylabel='Percent', xlabel='Year label')
axes[1].plot(aligned.purchase_year, aligned[share_col],
             marker='o', color=FOOT_LOCKER, linewidth=2.5)
axes[1].set(title='Foot Locker purchases from Nike', ylabel='Percent', xlabel='Year label')
for ax in axes:
    style_axes(ax)
add_logo_label(axes[0], 'Nike', x=.02, y=.93, text='Nike Direct')
add_logo_label(axes[1], 'Nike', x=.02, y=.93, text='Nike supplier share')
plt.show()
""")

set_source(nb.cells[66], r"""
claim_matrix = pd.DataFrame([
    {'claim': 'Nike shifted toward company-operated channels',
     'available_measure': 'Nike Direct share',
     'support_level': 'directly measured',
     'remaining_gap': 'Direct combines owned stores and digital'},
    {'claim': 'Foot Locker reduced dependence on Nike',
     'available_measure': 'Nike share of Foot Locker merchandise purchases',
     'support_level': 'directly measured at one retailer',
     'remaining_gap': 'Not running-specific and not consumer sell-through'},
    {'claim': 'Deckers and On expanded wholesale faster',
     'available_measure': 'Indexed reported wholesale revenue',
     'support_level': 'directly measured within company scope',
     'remaining_gap': 'Different fiscal calendars, scopes, currencies and price/unit mix'},
    {'claim': 'Nike caused competitor growth',
     'available_measure': 'Coincident annual company and retailer trends',
     'support_level': 'not identified',
     'remaining_gap': 'No treated/control store panel or account-change dates'},
    {'claim': 'Nike lost global running market share',
     'available_measure': 'No consistent independent share series in these files',
     'support_level': 'not measured',
     'remaining_gap': 'Need category units/value by brand and geography'},
])
display(claim_matrix)
""")

set_source(nb.cells[68], r"""
alternatives = pd.DataFrame({'alternative_explanation': [
    'Deckers and On product innovation and brand demand',
    'Overall performance-running category growth',
    'COVID store closures and channel migration',
    'Supply-chain availability and inventory differences',
    "Foot Locker's own assortment and diversification strategy",
    'Pricing, currency and product-mix changes in reported revenue',
    'Different geographic expansion and store footprints',
]})
display(alternatives)
""")

set_source(nb.cells[79], r"""
fig_dashboard, axes = plt.subplots(2, 2, figsize=(14, 9), layout='constrained')
axes[0, 0].bar(nike.fiscal_year, nike.nike_brand_wholesale / 1000,
               label='Wholesale', color=CHANNEL_COLORS['Wholesale'])
axes[0, 0].bar(nike.fiscal_year, nike.nike_brand_direct / 1000,
               bottom=nike.nike_brand_wholesale / 1000,
               label='Nike Direct', color=CHANNEL_COLORS['Direct'])
axes[0, 0].set(title='A. Nike channel revenue', ylabel='USD billions')
axes[0, 0].legend(frameon=False)
add_logo_label(axes[0, 0], 'Nike', x=.76, y=.93, fontsize=8)

for company, group in wholesale_chart.groupby('company'):
    group = group.sort_values('fiscal_year')
    axes[0, 1].plot(group.fiscal_year, group.wholesale_index_base,
                    marker='o', color=COMPANY_COLORS[company])
axes[0, 1].set(title='B. Wholesale growth',
               ylabel='Index: first available year = 100')
axes[0, 1].set_xticks(range(2019, 2025))
add_company_labels(axes[0, 1], ['Deckers', 'Nike', 'On'], fontsize=8)

for company, group in direct_mix.groupby('company'):
    group = group.sort_values('fiscal_year')
    axes[1, 0].plot(group.fiscal_year, group.direct_share_pct,
                    marker='o', color=COMPANY_COLORS[company])
axes[1, 0].set(title='C. Company-operated channel share', ylabel='Percent')
add_company_labels(axes[1, 0], ['Deckers', 'Nike', 'On'], fontsize=8)

axes[1, 1].plot(foot_locker.purchase_year, foot_locker[share_col],
                marker='o', color=FOOT_LOCKER, linewidth=2.5)
axes[1, 1].set(title='D. Foot Locker purchases from Nike', ylabel='Percent', ylim=(0, 100))
add_logo_label(axes[1, 1], 'Nike', x=.02, y=.93, text='Nike supplier share', fontsize=8)

for ax in axes.flat:
    ax.set_xlabel('Fiscal-year / purchase-year label')
    style_axes(ax)
plt.show()
""")

set_source(nb.cells[81], r"""
output.mkdir(parents=True, exist_ok=True)
tables = {
    'nike_channel_analysis': nike,
    'peer_channel_analysis': peers,
    'wholesale_chart_2019_2024': wholesale_chart,
    'wholesale_comparison': comparison,
    'wholesale_growth_summary': growth_summary,
    'foot_locker_analysis': foot_locker,
    'aligned_retailer_evidence': aligned,
    'nike_endpoint_changes': nike_endpoints,
    'claim_matrix': claim_matrix,
    'alternative_explanations': alternatives,
    'research_scorecard': scorecard,
    'equity_price_index': price_index,
    'event_ledger': events,
}
for name, table in tables.items():
    table.to_csv(output / f'{name}.csv', index=False)
for name, figure in [('nike_channels', fig_nike), ('wholesale_index', fig_wholesale),
                     ('direct_mix', fig_direct), ('foot_locker', fig_fl),
                     ('aligned_retailer', fig_alignment),
                     ('equity_prices_with_events', fig_price_events),
                     ('dashboard', fig_dashboard)]:
    figure.savefig(output / f'{name}.png', dpi=160, bbox_inches='tight',
                   facecolor=BACKGROUND)
manifest = {'notebook': 'research/nike_distribution_case_study.ipynb',
            'preprocessing_manifest': 'data/preprocess/preprocessing_manifest.csv',
            'research_cutoff': research_cutoff.date().isoformat(),
            'generated_at_utc': pd.Timestamp.now(tz='UTC').isoformat(),
            'causal_estimate_produced': False, 'tables': list(tables)}
(output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
display(pd.Series({'results_directory': str(output)}))
""")

price_cells = [
    nbformat.v4.new_markdown_cell(r"""## Part 2B: Compare equity-price paths and event timing

Stock prices aggregate changing expectations about growth, margins, risk, interest rates and the
broader market. They can show when investors repriced each company, but they cannot isolate the
effect of distribution strategy by themselves.""",
        metadata={'tags': [PRICE_SECTION_TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 22A: Normalize adjusted stock prices

**Formula:** `Price index = adjusted close / first available adjusted close x 100`.

**Why?** Nike, Deckers and On trade at different dollar prices. Indexing each stock to 100 makes
their percentage paths comparable while preserving the actual daily observations.

> **ASSUMPTION:** Nike and Deckers use January 2, 2019 as their base. On uses its first available
> observation on September 15, 2021. The different base dates mean the chart compares paths, not
> equal holding-period returns. Yahoo adjusted close is used to account for reported splits and
> distributions.""",
        metadata={'tags': [PRICE_SECTION_TAG]}),
    nbformat.v4.new_code_cell(r"""prices = prices.sort_values(['company', 'date']).copy()
prices['base_date'] = prices.groupby('company').date.transform('first')
prices['base_adj_close'] = prices.groupby('company').adj_close.transform('first')
prices['price_index'] = 100 * prices.adj_close / prices.base_adj_close
price_index = prices[['date', 'company', 'ticker', 'adj_close', 'base_date',
                      'base_adj_close', 'price_index', 'source_url']].copy()
assert np.allclose(price_index.groupby('company').price_index.first(), 100)
display(price_index.groupby('company').agg(
    first_date=('date', 'min'), last_date=('date', 'max'), observations=('date', 'size')))
""", metadata={'tags': [PRICE_SECTION_TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 22B: Build the event ledger

**Formula or operation:** Record a small set of dated strategy, retailer, leadership and macro
events, with one primary source URL for each marker.

**Why?** Event markers make the timeline readable without claiming an event caused the nearby
price move. The selected events are directly relevant to the distribution thesis or footwear
input-cost risk:

- [Nike Consumer Direct Acceleration operating-model update](https://investors.nike.com/investors/news-events-and-reports/investor-news/investor-news-details/2020/Nike-Announces-Senior-Leadership-Changes-to-Unlock-Future-Growth-Through-the-Consumer-Direct-Acceleration/default.aspx)
- [Foot Locker vendor-mix and diversification update](https://investors.footlocker-inc.com/news-releases/news-release-details/foot-locker-inc-reports-2021-fourth-quarter-and-full-year)
- [Nike announcement of Elliott Hill as CEO](https://about.nike.com/en/newsroom/releases/nike-inc-announces-return-of-long-time-nike-veteran-elliott-hill-as-president-and-ceo)
- [White House April 2, 2025 reciprocal-tariff announcement](https://www.whitehouse.gov/fact-sheets/2025/04/fact-sheet-president-donald-j-trump-declares-national-emergency-to-increase-our-competitive-edge-protect-our-sovereignty-and-strengthen-our-national-and-economic-security/)

> **ASSUMPTION:** These are contextual milestones selected for this case study, not a complete
> event study. No market-model adjustment, statistical significance test or causal attribution is
> performed.""",
        metadata={'tags': [PRICE_SECTION_TAG]}),
    nbformat.v4.new_code_cell(r"""events = pd.DataFrame([
    {'event_date': '2020-07-22', 'event': 'CDA operating-model update',
     'category': 'strategy',
     'source_url': 'https://investors.nike.com/investors/news-events-and-reports/investor-news/investor-news-details/2020/Nike-Announces-Senior-Leadership-Changes-to-Unlock-Future-Growth-Through-the-Consumer-Direct-Acceleration/default.aspx'},
    {'event_date': '2022-02-25', 'event': 'Foot Locker vendor-mix reset',
     'category': 'retailer',
     'source_url': 'https://investors.footlocker-inc.com/news-releases/news-release-details/foot-locker-inc-reports-2021-fourth-quarter-and-full-year'},
    {'event_date': '2024-09-19', 'event': 'Elliott Hill announced as CEO',
     'category': 'leadership',
     'source_url': 'https://about.nike.com/en/newsroom/releases/nike-inc-announces-return-of-long-time-nike-veteran-elliott-hill-as-president-and-ceo'},
    {'event_date': '2025-04-02', 'event': 'Liberation Day tariffs announced',
     'category': 'macro',
     'source_url': 'https://www.whitehouse.gov/fact-sheets/2025/04/fact-sheet-president-donald-j-trump-declares-national-emergency-to-increase-our-competitive-edge-protect-our-sovereignty-and-strengthen-our-national-and-economic-security/'},
])
events['event_date'] = pd.to_datetime(events.event_date)
assert events.event_date.between(research_start, research_cutoff).all()
assert events.source_url.str.startswith('https://').all()
display(events)
""", metadata={'tags': [PRICE_SECTION_TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 22C: Plot indexed prices with event markers

**Formula or operation:** Draw each daily price index and add a vertical line on every event date.
Company logos appear only inside the fixed-size series labels.

**Why?** This combines market expectations and the strategic timeline in one view. Read changes
around an event as a prompt for further research, not as an event-return estimate.""",
        metadata={'tags': [PRICE_SECTION_TAG]}),
    nbformat.v4.new_code_cell(r"""fig_price_events, ax = plt.subplots(figsize=(14, 6.5), layout='constrained')
for company, group in price_index.groupby('company'):
    ax.plot(group.date, group.price_index, color=COMPANY_COLORS[company],
            linewidth=1.8, alpha=.95)

for level, event in enumerate(events.itertuples()):
    color = EVENT_COLORS[event.category]
    ax.axvline(event.event_date, color=color, linewidth=1.2, alpha=.9)
    ax.text(event.event_date, .05 + .18 * (level % 2),
            f'{event.event_date:%b %Y}  {event.event}',
            transform=ax.get_xaxis_transform(), rotation=90,
            color=color, fontsize=8, va='bottom', ha='right',
            bbox={'facecolor': PANEL_BACKGROUND, 'edgecolor': 'none', 'alpha': .82, 'pad': 2})

ax.axhline(100, color=REFERENCE, linewidth=1)
ax.set(title='Adjusted stock-price paths and distribution-related events',
       xlabel='Trading date', ylabel='Index: each ticker first observation = 100')
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax.margins(x=.01, y=.12)
style_axes(ax)
add_company_labels(ax, ['Deckers', 'Nike', 'On'])
plt.show()
""", metadata={'tags': [PRICE_SECTION_TAG]}),
]

part_three_index = next(
    i for i, cell in enumerate(nb.cells)
    if cell.cell_type == 'markdown' and cell.source.startswith('## Part 3:')
)
nb.cells[part_three_index:part_three_index] = price_cells

# Keep the learning notebook reproducible and lightweight in version control.
for cell in nb.cells:
    if cell.cell_type == "code":
        cell["execution_count"] = None
        cell["outputs"] = []

nbformat.write(nb, NOTEBOOK)
print(f"Updated {NOTEBOOK.relative_to(ROOT)}")
