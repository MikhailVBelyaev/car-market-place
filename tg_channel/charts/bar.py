"""Horizontal bar chart for brand ranking posts."""
import io
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from .style import apply_base_style, pct_color, pct_arrow, BLUE, BG, GREY


def brand_ranking_chart(brands: list, title: str = "Top brands this week") -> io.BytesIO:
    """
    brands: list of {brand, count, avg_price, pct_change}
    Returns PNG bytes buffer.
    """
    brands = list(reversed(brands))   # highest bar at top
    labels = [b['brand'] for b in brands]
    counts = [b['count'] for b in brands]
    pcts   = [b.get('pct_change') for b in brands]

    fig, ax = plt.subplots(figsize=(10, max(5, len(brands) * 0.55 + 1.5)))
    apply_base_style(fig, ax)

    bar_colors = [pct_color(p) for p in pcts]
    bars = ax.barh(labels, counts, color=bar_colors, height=0.6, zorder=2)

    max_count = max(counts) if counts else 1
    for bar, brand_data in zip(bars, brands):
        count = brand_data['count']
        price = brand_data['avg_price']
        pct   = brand_data.get('pct_change')
        pct_txt = f'  {pct_arrow(pct)}' if pct is not None else ''
        ax.text(
            count + max_count * 0.01, bar.get_y() + bar.get_height() / 2,
            f'{count:,} e\'lon  ${price:,}{pct_txt}',
            va='center', ha='left', fontsize=8.5, color='#212121',
        )

    ax.set_xlim(0, max_count * 1.45)
    ax.set_xlabel("E'lonlar soni / Количество объявлений", fontsize=9, color=GREY)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=14, color='#212121')

    # Legend
    legend = [
        mpatches.Patch(color='#2E7D32', label="Ko'paydi / Рост"),
        mpatches.Patch(color='#C62828', label="Kamaydi / Снижение"),
    ]
    ax.legend(handles=legend, fontsize=8, loc='lower right')

    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x):,}'))
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf
