"""Shared matplotlib style for all channel charts."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Palette
BLUE       = '#1565C0'
BLUE_LIGHT = '#90CAF9'
GREEN      = '#2E7D32'
RED        = '#C62828'
GREY       = '#9E9E9E'
BG         = '#FAFAFA'
GRID       = '#E0E0E0'

BRAND_COLORS = [
    '#1565C0', '#1976D2', '#1E88E5', '#2196F3', '#42A5F5',
    '#64B5F6', '#90CAF9', '#BBDEFB', '#E3F2FD', '#F3F9FF',
]


def apply_base_style(fig, ax):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.grid(True, axis='x', color=GRID, linewidth=0.8, linestyle='--', zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(GRID)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(colors='#424242', labelsize=9)


def usd_formatter(x, _):
    return f'${x:,.0f}'


def pct_arrow(pct):
    if pct is None:
        return ''
    if pct > 0:
        return f'▲ +{pct:.1f}%'
    if pct < 0:
        return f'▼ {pct:.1f}%'
    return '— 0%'


def pct_color(pct):
    if pct is None:
        return GREY
    return GREEN if pct > 0 else (RED if pct < 0 else GREY)
