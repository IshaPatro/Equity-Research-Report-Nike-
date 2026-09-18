"""Apply the shared visual system and add an equity-research dashboard to the DCF."""

from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "research/model_nke_dcf.ipynb"
TAG = "dcf-dashboard"


def set_source(cell, source):
    cell.source = source.strip() + "\n"


def code_after_heading(notebook, heading):
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "markdown" and cell.source.startswith(heading):
            if notebook.cells[index + 1].cell_type != "code":
                raise RuntimeError(f"Expected code after {heading}")
            return notebook.cells[index + 1]
    raise RuntimeError(f"Could not find {heading}")


nb = nbformat.read(NOTEBOOK, as_version=4)
nb.cells = [cell for cell in nb.cells if TAG not in cell.get("metadata", {}).get("tags", [])]

for cell in nb.cells:
    if cell.cell_type == "markdown" and cell.source.startswith("## Sources and preparation"):
        price_row = (
            "| NKE price history | `data/raw/prices/nke.csv` | Yahoo Finance daily adjusted closes; "
            "used for the trailing price path in the overall target chart |\n"
        )
        if price_row not in cell.source:
            marker = "| Comparison price | Recorded project observation: $36.22 on September 15, 2026 | [Yahoo historical prices](https://finance.yahoo.com/quote/NKE/history/); cached project observation, not a live quote |\n"
            cell.source = cell.source.replace(marker, marker + price_row)
        break

set_source(code_after_heading(nb, "## Step 1:"), r"""
from pathlib import Path
import importlib
import json
import re
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import Circle, Wedge
from IPython.display import display
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
""")

set_source(code_after_heading(nb, "## Step 2:"), r"""
root = next(p for p in (Path.cwd(), *Path.cwd().parents)
            if (p / 'data/preprocess/historical_annual.csv').exists())
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import ui.constants as chart_constants
importlib.reload(chart_constants)
from ui.constants import (BACKGROUND, PANEL_BACKGROUND, TEXT, MUTED_TEXT, GRID,
                          REFERENCE, NIKE, COMPANY_COLORS, CHANNEL_COLORS,
                          LOGO_FILES, LOGO_DISPLAY_PX, SCENARIO_COLORS,
                          VALUATION_COLORS, HEATMAP_COLORS, SIGNAL_COLORS)

prepared = root / 'data/preprocess'
output = root / 'data/results/dcf_learning'
logo_dir = root / 'data/logo'
analysis_start = pd.Timestamp('2019-01-01', tz='UTC')
valuation_time = pd.Timestamp('2026-09-15 16:00', tz='America/New_York')
cutoff_utc = valuation_time.tz_convert('UTC')
valuation_date = pd.Timestamp(valuation_time.date())
fiscal_base = pd.Timestamp('2026-05-31')

assert (logo_dir / LOGO_FILES['Nike']).exists()
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


def style_axes(ax, grid_axis='y'):
    ax.set_facecolor(PANEL_BACKGROUND)
    ax.grid(axis=grid_axis, color=GRID, linewidth=.8, alpha=.7)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.tick_params(colors=MUTED_TEXT)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)


def nike_logo_array():
    image = plt.imread(logo_dir / LOGO_FILES['Nike'])
    alpha = image[..., 3] if image.shape[-1] == 4 else np.ones(image.shape[:2])
    visible = np.argwhere(alpha > .02)
    y0, x0 = visible.min(axis=0)
    y1, x1 = visible.max(axis=0) + 1
    alpha = alpha[y0:y1, x0:x1]
    stride = max(1, int(np.ceil(max(alpha.shape) / 160)))
    alpha = alpha[::stride, ::stride]
    tinted = np.zeros((*alpha.shape, 4), dtype=float)
    tinted[..., :3] = to_rgb(NIKE)
    tinted[..., 3] = alpha
    return tinted


def add_nike_label(ax, x=.02, y=.92, text='Nike'):
    logo_array = nike_logo_array()
    image = OffsetImage(logo_array, zoom=LOGO_DISPLAY_PX / max(logo_array.shape[:2]))
    ax.add_artist(AnnotationBbox(image, (x, y), xycoords='axes fraction', frameon=False,
                                 box_alignment=(0, .5), pad=0, zorder=10))
    ax.annotate(text, xy=(x, y), xycoords='axes fraction',
                xytext=(LOGO_DISPLAY_PX + 8, 0), textcoords='offset points',
                color=NIKE, fontsize=9, fontweight='bold', va='center', zorder=10)
""")

set_source(code_after_heading(nb, "## Step 56:"), r"""
grid = sensitivity.pivot(index='wacc', columns='terminal_growth', values='value_per_share')
dcf_cmap = LinearSegmentedColormap.from_list('dcf_sensitivity', HEATMAP_COLORS)
fig_sensitivity, ax = plt.subplots(figsize=(8, 5), layout='constrained')
heat = ax.imshow(grid, cmap=dcf_cmap, aspect='auto')
ax.set_xticks(range(len(grid.columns)), [f'{x:.1%}' for x in grid.columns])
ax.set_yticks(range(len(grid.index)), [f'{x:.1%}' for x in grid.index])
for i in range(len(grid.index)):
    for j in range(len(grid.columns)):
        text_color = BACKGROUND if heat.norm(grid.iloc[i, j]) > .58 else TEXT
        ax.text(j, i, f'${grid.iloc[i, j]:.2f}', ha='center', va='center', color=text_color)
ax.set(title='Fundamental DCF sensitivity', xlabel='Terminal growth', ylabel='WACC')
ax.set_facecolor(PANEL_BACKGROUND)
ax.tick_params(colors=MUTED_TEXT)
for spine in ax.spines.values():
    spine.set_color(GRID)
colorbar = fig_sensitivity.colorbar(heat, ax=ax, label='USD per share')
colorbar.ax.tick_params(colors=MUTED_TEXT)
colorbar.set_label('USD per share', color=TEXT)
colorbar.outline.set_edgecolor(GRID)
plt.show()
""")

set_source(code_after_heading(nb, "## Step 57:"), r"""
fig_forecast, axes = plt.subplots(1, 2, figsize=(11, 4), layout='constrained')
for name, group in forecast.groupby('case'):
    axes[0].plot(group.fiscal_year, group.revenue / 1e9, marker='o',
                 label=name.title(), color=SCENARIO_COLORS[name], linewidth=2.4)
    axes[1].plot(group.fiscal_year, group.margin * 100, marker='o',
                 label=name.title(), color=SCENARIO_COLORS[name], linewidth=2.4)
axes[0].set(title='Forecast revenue', ylabel='USD billions')
axes[1].set(title='Forecast operating margin', ylabel='Percent')
for ax in axes:
    ax.set_xticks(years)
    ax.set_xlabel('Fiscal year')
    style_axes(ax)
    ax.legend(frameon=False, ncol=3)
plt.show()
""")

set_source(code_after_heading(nb, "## Step 66:"), r"""
fig_prices, ax = plt.subplots(figsize=(9, 4), layout='constrained')
final_prices[['fundamental_value_per_share', 'adjusted_reference_price']].plot.bar(
    ax=ax, color=[VALUATION_COLORS['fundamental_value'],
                  VALUATION_COLORS['sentiment_value']], rot=0)
ax.axhline(comparison_price, color=VALUATION_COLORS['market_price'],
           linestyle='--', linewidth=1.3, label='September 15 close')
ax.set(title='DCF and final sentiment overlay', ylabel='USD per share', xlabel='Scenario')
style_axes(ax)
ax.legend(frameon=False, ncol=3)
plt.show()
""")

dashboard_cells = [
    nbformat.v4.new_markdown_cell(r"""## Price target and rating

The target and rating below are model outputs, not external analyst consensus. The range uses the
sentiment-adjusted bear, base and bull DCF values. The base case is the overall price target.
Green and red are reserved for recommendation or positive/negative signals throughout the DCF
visuals; operating scenarios use neutral colors.""",
        metadata={'tags': [TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 66A: Define the overall target and rating policy

**Formula:** `Target upside = base adjusted price / observed close - 1`.

**Rating rule:** Buy when upside is at least 15%; Sell when downside is at least 15%; otherwise
Hold.

**Why?** A price target and recommendation answer different questions. The target states the
model's estimated value, while the rating translates expected upside or downside into an explicit
policy band.

> **ASSUMPTION:** The plus/minus 15% thresholds are analyst-selected and uncalibrated. The base
> sentiment-adjusted DCF is treated as the overall target as of the valuation date, not as a
> consensus target or guaranteed future trading price. The price-target chart displays a one-year
> horizon for readability; it does not turn the point-in-time DCF value into a timed forecast.""",
        metadata={'tags': [TAG]}),
    nbformat.v4.new_code_cell(r"""price_target_summary = final_prices[['adjusted_reference_price']].rename(
    columns={'adjusted_reference_price': 'price_target'})
price_target_summary['observed_close'] = comparison_price
price_target_summary['upside'] = price_target_summary.price_target / comparison_price - 1

nke_price_path = root / 'data/raw/prices/nke.csv'
nke_prices = pd.read_csv(nke_price_path, parse_dates=['date'])
nke_prices = nke_prices.loc[nke_prices.date.le(valuation_date)].copy()
assert nke_prices.ticker.eq('NKE').all()
assert nke_prices.adj_close.gt(0).all()
assert np.isclose(nke_prices.iloc[-1].adj_close, comparison_price, atol=.01)
price_window_start = valuation_date - pd.DateOffset(years=1)
nke_price_window = nke_prices.loc[nke_prices.date.ge(price_window_start)].copy()
target_display_date = valuation_date + pd.DateOffset(years=1)
price_target_summary['target_display_date'] = target_display_date.date().isoformat()

buy_threshold = .15
sell_threshold = -.15
overall_target = float(price_target_summary.loc['base', 'price_target'])
overall_upside = float(price_target_summary.loc['base', 'upside'])
overall_rating = ('Buy' if overall_upside >= buy_threshold else
                  'Sell' if overall_upside <= sell_threshold else 'Hold')
rating_summary = pd.DataFrame([{
    'rating': overall_rating, 'overall_price_target': overall_target,
    'observed_close': comparison_price, 'upside': overall_upside,
    'buy_threshold': buy_threshold, 'sell_threshold': sell_threshold,
    'valuation_date': valuation_date.date().isoformat(),
}])
display(rating_summary)
""", metadata={'tags': [TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 66B: Plot the overall price-target range

**Formula or operation:** Plot the trailing twelve months of NKE adjusted closes, then extend
dashed paths from the observed close to the adjusted bear, base and bull values at a one-year
display date.

**Why?** The chart gives the target range a market-price context. The base path is labelled
Average, while bear and bull become Low and High.

> **ASSUMPTION:** The one-year date is a visual display convention only. The dashed lines are not
> a forecast of the route that NKE shares will take, nor an event-study estimate.""",
        metadata={'tags': [TAG]}),
    nbformat.v4.new_code_cell(r"""import matplotlib.dates as mdates

fig_price_target, (ax, label_ax) = plt.subplots(
    1, 2, figsize=(14, 5.5), layout='constrained',
    gridspec_kw={'width_ratios': [5.5, 1.25]})
scenario_order = ['bear', 'base', 'bull']
target_values = price_target_summary.loc[scenario_order, 'price_target']
target_labels = {'bear': 'Low', 'base': 'Average', 'bull': 'High'}
ax.plot(nke_price_window.date, nke_price_window.adj_close,
        color=VALUATION_COLORS['historical_revenue'], linewidth=1.8,
        label='NKE adjusted close')
ax.scatter(valuation_date, comparison_price, s=46, color=VALUATION_COLORS['market_price'],
           edgecolor=BACKGROUND, linewidth=.8, zorder=4)
for name in scenario_order:
    value = target_values.loc[name]
    color = SCENARIO_COLORS[name]
    ax.plot([valuation_date, target_display_date], [comparison_price, value],
            color=color, linewidth=1.5, linestyle=(0, (3, 3)))
    label_ax.plot([.03, .23], [value, value], color=color, linewidth=6,
                  solid_capstyle='butt')
    label_ax.text(.30, value, f"{target_labels[name]}\n${value:.2f}",
                  color=TEXT, fontsize=11, va='center', ha='left')
ax.axvline(valuation_date, color=REFERENCE, linewidth=1, linestyle=':')
ax.text(valuation_date, comparison_price, f'  Observed close ${comparison_price:.2f}',
        color=TEXT, fontsize=9, va='bottom', ha='left')
ax.set(title=f'Overall price target: ${overall_target:.2f}',
       xlabel='Trading date and display horizon', ylabel='USD per share')
ax.set_xlim(price_window_start, target_display_date + pd.Timedelta(days=30))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
style_axes(ax)
label_ax.set_facecolor(PANEL_BACKGROUND)
label_ax.set_xlim(0, 1)
label_ax.set_xticks([])
label_ax.set_yticks([])
for spine in label_ax.spines.values():
    spine.set_visible(False)
label_ax.set_ylim(ax.get_ylim())
plt.show()
""", metadata={'tags': [TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 66C: Plot the overall rating

**Formula or operation:** Map base-case upside to the Sell, Hold or Buy policy band.

**Why?** A gauge communicates the recommendation separately from the dollar target. The needle
uses continuous upside, while the displayed word follows the threshold rule above.

> **ASSUMPTION:** The gauge clips visual positioning at plus/minus 30% so extreme values remain
> readable. The rating calculation itself is not clipped.""",
        metadata={'tags': [TAG]}),
    nbformat.v4.new_code_cell(r"""fig_rating, ax = plt.subplots(figsize=(7, 4.5), layout='constrained')
segments = [(120, 180, 'sell', 'Sell'), (60, 120, 'hold', 'Hold'),
            (0, 60, 'buy', 'Buy')]
for start, end, key, label in segments:
    ax.add_patch(Wedge((0, 0), 1, start, end, width=.22,
                       facecolor=SIGNAL_COLORS[key], edgecolor=BACKGROUND))
    angle = np.deg2rad((start + end) / 2)
    ax.text(.83 * np.cos(angle), .83 * np.sin(angle), label,
            ha='center', va='center', color=TEXT, fontsize=9, fontweight='bold')

gauge_upside = np.clip(overall_upside, -.30, .30)
needle_angle = np.deg2rad(180 - (gauge_upside + .30) / .60 * 180)
ax.plot([0, .72 * np.cos(needle_angle)], [0, .72 * np.sin(needle_angle)],
        color=TEXT, linewidth=3, solid_capstyle='round')
ax.add_patch(Circle((0, 0), .045, color=TEXT))
rating_color = SIGNAL_COLORS[overall_rating.lower()]
ax.text(0, -.13, overall_rating, ha='center', va='top',
        color=rating_color, fontsize=34, fontweight='bold')
ax.text(0, -.32, f'{overall_upside:+.1%} vs observed close',
        ha='center', va='top', color=MUTED_TEXT, fontsize=11)
ax.set(title='Overall DCF rating', xlim=(-1.12, 1.12), ylim=(-.45, 1.12), aspect='equal')
ax.set_facecolor(PANEL_BACKGROUND)
ax.axis('off')
plt.show()
""", metadata={'tags': [TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Equity research dashboard

The dashboard brings the operating history, forecast requirements, cash generation and valuation
range into one review surface. It is a diagnostic summary, not a substitute for the detailed
calculations above. The Nike logo is used once, as part of the dashboard label.""",
        metadata={'tags': [TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 66D: Prepare dashboard views

**Formula or operation:** Select historical operating measures, the base-case cash-flow path,
enterprise-value components and scenario values per share.

**Why?** A good equity-research dashboard connects the target price to the historical evidence,
the operating assumptions required to reach it, and the share of value that depends on the
terminal period.""",
        metadata={'tags': [TAG]}),
    nbformat.v4.new_code_cell(r"""historical_view = anchors[['period_end', 'revenue', 'gross_margin',
                                   'operating_margin']].copy()
historical_view['fiscal_year'] = historical_view.period_end.dt.year
base_case = forecast.loc[forecast.case.eq('base')].copy()
value_mix = valuation[['pv_explicit', 'pv_terminal', 'terminal_share_of_ev']].copy()
dashboard_prices = final_prices[['fundamental_value_per_share',
                                 'adjusted_reference_price']].copy()
display(pd.Series({'historical_years': len(historical_view),
                   'forecast_years': len(base_case),
                   'scenarios': len(dashboard_prices)}))
""", metadata={'tags': [TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 66E: Plot historical operating performance

**Formula or operation:** Show reported revenue and the gross- and operating-margin history.

**Why?** Forecasts should be anchored to what Nike has actually earned. Revenue shows scale;
the two margins separate product economics from the operating-cost structure.""",
        metadata={'tags': [TAG]}),
    nbformat.v4.new_code_cell(r"""fig_history, axes = plt.subplots(1, 2, figsize=(11, 4), layout='constrained')
axes[0].bar(historical_view.fiscal_year, historical_view.revenue / 1e9,
            color=VALUATION_COLORS['historical_revenue'])
axes[0].set(title='Historical revenue', xlabel='Fiscal year', ylabel='USD billions')
axes[1].plot(historical_view.fiscal_year, historical_view.gross_margin * 100,
             marker='o', linewidth=2.4, label='Gross margin',
             color=VALUATION_COLORS['gross_margin'])
axes[1].plot(historical_view.fiscal_year, historical_view.operating_margin * 100,
             marker='o', linewidth=2.4, label='Operating margin',
             color=VALUATION_COLORS['operating_margin'])
axes[1].set(title='Historical margins', xlabel='Fiscal year', ylabel='Percent')
for ax in axes:
    ax.set_xticks(historical_view.fiscal_year)
    style_axes(ax)
axes[1].legend(frameon=False)
plt.show()
""", metadata={'tags': [TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 66F: Plot base-case cash generation

**Formula or operation:** Compare stub-adjusted FCFF with its discounted present value for each
forecast year.

**Why?** This reveals both the cash-flow ramp and the value lost to time and risk. A distant cash
flow can be economically important while contributing less present value today.""",
        metadata={'tags': [TAG]}),
    nbformat.v4.new_code_cell(r"""fig_fcff, ax = plt.subplots(figsize=(9, 4), layout='constrained')
x = np.arange(len(base_case))
width = .36
ax.bar(x - width / 2, base_case.fcff_remaining / 1e9, width,
       label='Remaining FCFF', color=VALUATION_COLORS['fcff'])
ax.bar(x + width / 2, base_case.pv_fcff / 1e9, width,
       label='Present value', color=VALUATION_COLORS['pv_fcff'])
ax.set_xticks(x, base_case.fiscal_year)
ax.set(title='Base-case cash generation', xlabel='Fiscal year', ylabel='USD billions')
style_axes(ax)
ax.legend(frameon=False)
plt.show()
""", metadata={'tags': [TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 66G: Plot enterprise-value composition

**Formula or operation:** Enterprise value = explicit-period present value + terminal-value
present value.

**Why?** A high terminal share means the conclusion depends heavily on assumptions beyond the
five-year forecast. This is one of the most important DCF risk checks.""",
        metadata={'tags': [TAG]}),
    nbformat.v4.new_code_cell(r"""fig_value_mix, ax = plt.subplots(figsize=(9, 4), layout='constrained')
positions = np.arange(len(value_mix))
explicit = value_mix.pv_explicit / 1e9
terminal_pv = value_mix.pv_terminal / 1e9
ax.bar(positions, explicit, label='Explicit forecast',
       color=VALUATION_COLORS['explicit_value'])
ax.bar(positions, terminal_pv, bottom=explicit, label='Terminal value',
       color=VALUATION_COLORS['terminal_value'])
for position, share, total in zip(positions, value_mix.terminal_share_of_ev,
                                  explicit + terminal_pv):
    ax.text(position, total, f'{share:.0%} terminal', ha='center', va='bottom', color=TEXT)
ax.set_xticks(positions, [name.title() for name in value_mix.index])
ax.set(title='Enterprise-value composition', xlabel='Scenario', ylabel='USD billions')
style_axes(ax)
ax.legend(frameon=False)
plt.show()
""", metadata={'tags': [TAG]}),
    nbformat.v4.new_markdown_cell(r"""## Step 66H: Assemble the equity-research dashboard

**Formula or operation:** Combine six complementary views using the same prepared tables and
valuation outputs calculated above.

**Why?** The dashboard lets an analyst move from historical evidence to forecast assumptions,
cash generation and valuation without hiding the model's terminal-value dependence.

> **ASSUMPTION:** The dashboard introduces no new forecast or valuation assumptions. It only
> visualizes calculations already made in the notebook.""",
        metadata={'tags': [TAG]}),
    nbformat.v4.new_code_cell(r"""fig_dashboard, axes = plt.subplots(3, 2, figsize=(15, 13), layout='constrained')

axes[0, 0].bar(historical_view.fiscal_year, historical_view.revenue / 1e9,
               color=VALUATION_COLORS['historical_revenue'])
axes[0, 0].set(title='A. Historical revenue', ylabel='USD billions')
axes[0, 0].set_xticks(historical_view.fiscal_year)
add_nike_label(axes[0, 0], text='Nike DCF dashboard')

axes[0, 1].plot(historical_view.fiscal_year, historical_view.gross_margin * 100,
                marker='o', label='Gross margin', color=VALUATION_COLORS['gross_margin'])
axes[0, 1].plot(historical_view.fiscal_year, historical_view.operating_margin * 100,
                marker='o', label='Operating margin', color=VALUATION_COLORS['operating_margin'])
axes[0, 1].set(title='B. Historical margins', ylabel='Percent')
axes[0, 1].set_xticks(historical_view.fiscal_year)
axes[0, 1].legend(frameon=False)

for name, group in forecast.groupby('case'):
    axes[1, 0].plot(group.fiscal_year, group.revenue / 1e9, marker='o',
                    label=name.title(), color=SCENARIO_COLORS[name])
    axes[1, 1].plot(group.fiscal_year, group.margin * 100, marker='o',
                    label=name.title(), color=SCENARIO_COLORS[name])
axes[1, 0].set(title='C. Scenario revenue', ylabel='USD billions')
axes[1, 1].set(title='D. Scenario operating margin', ylabel='Percent')
axes[1, 0].set_xticks(years)
axes[1, 1].set_xticks(years)
axes[1, 0].legend(frameon=False, ncol=3)
axes[1, 1].legend(frameon=False, ncol=3)

axes[2, 0].bar(base_case.fiscal_year - .18, base_case.fcff_remaining / 1e9, .36,
               label='Remaining FCFF', color=VALUATION_COLORS['fcff'])
axes[2, 0].bar(base_case.fiscal_year + .18, base_case.pv_fcff / 1e9, .36,
               label='Present value', color=VALUATION_COLORS['pv_fcff'])
axes[2, 0].set(title='E. Base-case FCFF', ylabel='USD billions')
axes[2, 0].set_xticks(base_case.fiscal_year)
axes[2, 0].legend(frameon=False)

scenario_positions = np.arange(len(dashboard_prices))
axes[2, 1].bar(scenario_positions, dashboard_prices.fundamental_value_per_share,
               color=[SCENARIO_COLORS[name] for name in dashboard_prices.index])
axes[2, 1].axhline(comparison_price, color=VALUATION_COLORS['market_price'],
                   linestyle='--', linewidth=1.3, label='Observed close')
axes[2, 1].set_xticks(scenario_positions,
                      [name.title() for name in dashboard_prices.index])
axes[2, 1].set(title='F. Fundamental value per share', ylabel='USD per share')
axes[2, 1].legend(frameon=False)

for ax in axes.flat:
    style_axes(ax)
    ax.set_xlabel('Fiscal year' if ax is not axes[2, 1] else 'Scenario')
plt.show()
""", metadata={'tags': [TAG]}),
]

input_ledger_index = next(
    index for index, cell in enumerate(nb.cells)
    if cell.cell_type == "markdown" and cell.source.startswith("## Step 67:")
)
nb.cells[input_ledger_index:input_ledger_index] = dashboard_cells

save_cell = code_after_heading(nb, "## Step 68:")
save_cell.source = save_cell.source.replace(
    "for name, figure in [('forecast_paths', fig_forecast), ('sensitivity', fig_sensitivity),\n"
    "                     ('price_comparison', fig_prices)]:",
    "for name, figure in [('forecast_paths', fig_forecast), ('sensitivity', fig_sensitivity),\n"
    "                     ('price_comparison', fig_prices), ('historical_performance', fig_history),\n"
    "                     ('base_fcff', fig_fcff), ('valuation_mix', fig_value_mix),\n"
    "                     ('equity_research_dashboard', fig_dashboard)]:",
)
save_cell.source = save_cell.source.replace(
    "figure.savefig(output / f'{name}.png', dpi=160, bbox_inches='tight')",
    "figure.savefig(output / f'{name}.png', dpi=160, bbox_inches='tight', facecolor=BACKGROUND)",
)
if "'price_target_summary': price_target_summary" not in save_cell.source:
    save_cell.source = save_cell.source.replace(
        "'input_ledger': input_ledger, 'sec_fact_audit': audit_nike}",
        "'input_ledger': input_ledger, 'price_target_summary': price_target_summary,\n"
        "          'rating_summary': rating_summary, 'sec_fact_audit': audit_nike}",
    )
if "'nke_price_history': nke_price_window" not in save_cell.source:
    save_cell.source = save_cell.source.replace(
        "'input_ledger': input_ledger, 'price_target_summary': price_target_summary,",
        "'input_ledger': input_ledger, 'nke_price_history': nke_price_window,\n"
        "          'price_target_summary': price_target_summary,",
    )
if "('overall_price_target', fig_price_target)" not in save_cell.source:
    save_cell.source = save_cell.source.replace(
        "('price_comparison', fig_prices), ('historical_performance', fig_history),",
        "('price_comparison', fig_prices), ('overall_price_target', fig_price_target),\n"
        "                     ('overall_rating', fig_rating), ('historical_performance', fig_history),",
    )

for cell in nb.cells:
    if cell.cell_type == "code":
        cell.execution_count = None
        cell.outputs = []

nbformat.write(nb, NOTEBOOK)
print(f"Updated {NOTEBOOK.relative_to(ROOT)}")
