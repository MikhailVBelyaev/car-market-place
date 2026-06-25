"""Monthly post: which car colors hold value best."""
import io
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from datetime import date
from charts.style import apply_base_style, BLUE, GREEN, RED, GREY, BG, pct_arrow


def fetch(django_url):
    r = requests.get(f"{django_url}/api/cars/analytics/color-premium/", timeout=15)
    r.raise_for_status()
    return r.json()


def build_chart(data):
    colors_data = data['colors']
    market_avg  = data['market_avg']
    today = date.today().strftime('%d.%m.%Y')

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG)
    apply_base_style(fig, ax)

    labels = [c['color'] for c in colors_data]
    pcts   = [c['vs_market_pct'] for c in colors_data]
    bar_colors = [GREEN if p >= 0 else RED for p in pcts]

    y = np.arange(len(labels))
    bars = ax.barh(y, pcts, color=bar_colors, height=0.6, zorder=2)
    ax.axvline(0, color=GREY, linewidth=1)
    for i, (bar, c) in enumerate(zip(bars, colors_data)):
        sign = '+' if c['vs_market_pct'] >= 0 else ''
        ax.text(c['vs_market_pct'] + (0.3 if c['vs_market_pct'] >= 0 else -0.3), i,
                f"{sign}{c['vs_market_pct']:.1f}%  avg ${c['avg_price']:,}",
                va='center', ha='left' if c['vs_market_pct'] >= 0 else 'right',
                fontsize=8.5, color='#212121')
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_title(
        f"Rang bo'yicha narx / Tseny po tsvetu  ·  {today}\n"
        f"(bozor o'rtachasiga nisbatan / otnositelno srednego ${market_avg:,})",
        fontsize=10, fontweight='bold', color='#212121')
    ax.set_xlabel("Bozordan farq, % / Otkloneniye ot rynka, %", fontsize=8.5, color=GREY)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(data):
    today  = date.today().strftime('%d.%m.%Y')
    mktavg = data['market_avg']
    top    = data['colors']

    uz = '\n'.join(
        f"  {'▲' if c['vs_market_pct']>=0 else '▼'} {c['color']}: avg ${c['avg_price']:,} ({'+' if c['vs_market_pct']>=0 else ''}{c['vs_market_pct']:.1f}%)"
        for c in top[:5])
    ru = '\n'.join(
        f"  {'▲' if c['vs_market_pct']>=0 else '▼'} {c['color']}: avg ${c['avg_price']:,} ({'+' if c['vs_market_pct']>=0 else ''}{c['vs_market_pct']:.1f}%)"
        for c in top[:5])

    return (
        f"\U0001f3a8 *RANG VA NARX · {today}*\nBozor o'rtachasi: ${mktavg:,}\n\n"
        f"Qaysi rang qimmatroq?\n{uz}\n\n"
        f"\U0001f4a1 _O'z mashinangiz bozor narxi:_\n\U0001f449 @MVehicleBot\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"\U0001f3a8 *TSVET I TSENA · {today}*\nSrednyaya po rynku: ${mktavg:,}\n\n"
        f"Kakoy tsvet dorozhe?\n{ru}\n\n"
        f"\U0001f4a1 _Uznat' tsenu svoey mashiny:_\n\U0001f449 @MVehicleBot"
    )


def run(django_url):
    data = fetch(django_url)
    return build_chart(data), build_text(data)
