"""Lollipop chart for price movers (risers + fallers)."""
import io
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from .style import apply_base_style, GREEN, RED, GREY, BG


def price_movers_chart(risers: list, fallers: list, period_days: int = 7) -> io.BytesIO:
    """
    risers/fallers: list of {brand, model, change_pct, avg_price}
    Returns PNG bytes buffer.
    """
    items  = list(reversed(fallers)) + [None] + risers
    labels = []
    values = []
    colors = []
    for item in items:
        if item is None:
            labels.append('')
            values.append(0)
            colors.append(GREY)
        else:
            labels.append(f"{item['brand']} {item['model']}")
            values.append(item['change_pct'])
            colors.append(GREEN if item['change_pct'] > 0 else RED)

    fig, ax = plt.subplots(figsize=(10, max(5, len(labels) * 0.6 + 1.5)))
    apply_base_style(fig, ax)
    ax.grid(True, axis='x', color='#E0E0E0', linewidth=0.8, linestyle='--', zorder=0)

    y_pos = range(len(labels))
    for i, (val, col) in enumerate(zip(values, colors)):
        if labels[i] == '':
            continue
        ax.plot([0, val], [i, i], color=col, linewidth=2, zorder=2)
        ax.scatter([val], [i], color=col, s=80, zorder=3)
        sign = '+' if val > 0 else ''
        ax.text(val + (0.2 if val >= 0 else -0.2), i,
                f'{sign}{val:.1f}%',
                va='center', ha='left' if val >= 0 else 'right',
                fontsize=8.5, color='#212121')

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=9)
    ax.axvline(0, color='#9E9E9E', linewidth=1, zorder=1)
    ax.set_xlabel("Narx o'zgarishi (%) / Изменение цены (%)", fontsize=9, color=GREY)
    ax.set_title(
        f"Narx o'zgarishlari (so'nggi {period_days} kun)\n"
        f"Изменения цен (последние {period_days} дней)",
        fontsize=12, fontweight='bold', pad=12, color='#212121'
    )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf
