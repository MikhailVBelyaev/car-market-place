"""Monthly post: price loss per 10,000 km for top models."""
import io
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import date
from charts.style import apply_base_style, BLUE, GREEN, RED, GREY, BG


def fetch(django_url):
    r = requests.get(f"{django_url}/api/cars/analytics/mileage-depreciation/", timeout=15)
    r.raise_for_status()
    return r.json()


def build_chart(data):
    models = data['models']
    today  = date.today().strftime('%d.%m.%Y')

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG)
    apply_base_style(fig, ax)

    labels = [f"{m['brand']} {m['model']}" for m in models]
    slopes = [abs(m['price_per_10k_km'])   for m in models]
    colors = [RED if m['price_per_10k_km'] < 0 else GREEN for m in models]

    bars = ax.barh(labels, slopes, color=colors, height=0.6, zorder=2)
    for bar, m in zip(bars, models):
        ax.text(bar.get_width() + (max(slopes) * 0.01 if slopes else 0),
                bar.get_y() + bar.get_height()/2,
                f"${abs(m['price_per_10k_km']):,.0f} / 10k km",
                va='center', fontsize=8.5, color='#212121')
    ax.set_xlim(0, max(slopes) * 1.45 if slopes else 1)
    ax.set_title(
        f"10 000 km uchun narq pasayishi / Poterya tseny za 10 000 km  ·  {today}",
        fontsize=10, fontweight='bold', color='#212121')
    ax.set_xlabel("$/10 000 km", fontsize=8.5, color=GREY)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(data):
    today  = date.today().strftime('%d.%m.%Y')
    models = data['models']
    uz = '\n'.join(
        f"  • {m['brand']} {m['model']}: ${abs(m['price_per_10k_km']):,.0f} / 10k km"
        for m in models)
    ru = uz
    return (
        f"\U0001f697 *YURISH VA NARQ · {today}*\n\n10 000 km uchun narq pasayishi:\n{uz}"
        "\n\n\U0001f449 @MVehicleBot\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"\U0001f697 *PROBEG I TSENA · {today}*\n\nPoterya tseny za 10 000 km:\n{ru}"
        "\n\n\U0001f449 @MVehicleBot"
    )


def run(django_url):
    data = fetch(django_url)
    return build_chart(data), build_text(data)
