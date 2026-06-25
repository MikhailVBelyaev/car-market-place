"""Monthly post: automatic vs manual price premium by brand."""
import io
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from datetime import date
from charts.style import apply_base_style, BLUE, GREEN, RED, GREY, BG


def fetch(django_url):
    r = requests.get(f"{django_url}/api/cars/analytics/gear-premium/", timeout=15)
    r.raise_for_status()
    return r.json()


def build_chart(data):
    brands = data['brands'][:6]
    today  = date.today().strftime('%d.%m.%Y')

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG)
    apply_base_style(fig, ax)

    labels    = [b['brand'] for b in brands]
    at_prices = [b['at_price'] for b in brands]
    mt_prices = [b['mt_price'] for b in brands]
    x = np.arange(len(labels))
    w = 0.35

    ax.bar(x - w/2, at_prices, w, label='Automatic (AT)', color=BLUE, zorder=2)
    ax.bar(x + w/2, mt_prices, w, label='Manual (MT)',    color=GREEN, alpha=0.8, zorder=2)

    for i, b in enumerate(brands):
        ax.text(i, max(b['at_price'], b['mt_price']) + 200,
                f"+{b['premium_pct']:.0f}%", ha='center', fontsize=8, color=BLUE, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_title(
        f"Avtomat va mexanik: narx farqi / Avtomat vs Mekhanika  ·  {today}",
        fontsize=10, fontweight='bold', color='#212121')
    ax.set_ylabel("O'rtacha narx / Srednyaya tsena ($)", fontsize=8.5, color=GREY)
    ax.legend(fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${int(x):,}'))

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(data):
    today  = date.today().strftime('%d.%m.%Y')
    brands = data['brands']

    lines_uz = '\n'.join(
        f"  • {b['brand']}: AT ${b['at_price']:,} vs MT ${b['mt_price']:,} (+{b['premium_pct']:.1f}%)"
        for b in brands[:5])
    lines_ru = lines_uz

    return (
        f"⚙️ *AVTOMAT VS MEXANIK · {today}*\n\n"
        f"Avtomat qancha qimmatroq?\n{lines_uz}\n\n"
        f"\U0001f449 @MVehicleBot\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚙️ *AVTOMAT VS MEKHANIKA · {today}*\n\n"
        f"Naskol'ko dorozhe avtomat?\n{lines_ru}\n\n"
        f"\U0001f449 @MVehicleBot"
    )


def run(django_url):
    data = fetch(django_url)
    return build_chart(data), build_text(data)
