"""Daily post: 'How much is a <model> worth right now?' — advertises the bot.

Dense, scannable price card for one popular model: current median price across
recent years, so a reader instantly sees where their own car sits and taps
through to @MVehicleBot to check the exact figure.

The featured model rotates by day-of-year so the channel stays fresh daily.
Data comes from the corrected per-model median endpoint (age-depreciation).
"""
import io
from datetime import date, datetime

import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from charts.style import apply_base_style, BLUE, BLUE_LIGHT, GREEN, GREY, BG

# Popular, high-volume models with reliable data. Rotates daily.
FEATURED = [
    ('Chevrolet', 'Cobalt'),  ('Chevrolet', 'Nexia'),   ('Chevrolet', 'Malibu'),
    ('Chevrolet', 'Lacetti'), ('Chevrolet', 'Spark'),   ('Chevrolet', 'Gentra'),
    ('Chevrolet', 'Onix'),    ('Chevrolet', 'Tracker'), ('Chevrolet', 'Captiva'),
    ('Chevrolet', 'Damas'),   ('BYD', 'Song'),          ('Hyundai', 'Elantra'),
]


def _pick():
    idx = datetime.now().timetuple().tm_yday % len(FEATURED)
    return FEATURED[idx]


def fetch(django_url, brand, model):
    r = requests.get(
        f"{django_url}/api/cars/analytics/age-depreciation/",
        params={'brand': brand, 'model': model}, timeout=15,
    )
    r.raise_for_status()
    models = r.json().get('models', [])
    return models[0] if models else None


def build_chart(entry):
    years = entry['years'][-8:]          # newest 8 years, keeps the card clean
    labels = [str(y['year']) for y in years]
    prices = [y['median_price'] for y in years]
    ypos   = list(range(len(labels)))

    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=BG)
    apply_base_style(fig, ax)

    colors = [BLUE] * len(prices)
    colors[-1] = GREEN                   # highlight the newest year
    ax.barh(ypos, prices, color=colors, height=0.62, zorder=3)

    for yi, p in zip(ypos, prices):
        ax.text(p + max(prices) * 0.01, yi, f"${p:,}",
                va='center', fontsize=9.5, color='#212121', fontweight='bold')

    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_title(
        f"{entry['brand']} {entry['model']} — narx / tsena  ·  {date.today():%d.%m.%Y}",
        fontsize=12, fontweight='bold', color='#212121')
    ax.set_xlabel("Mediana narx / Mediannaya tsena ($)", fontsize=9, color=GREY)
    ax.set_xlim(0, max(prices) * 1.15)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(entry):
    years = entry['years']
    name  = f"{entry['brand']} {entry['model']}"
    today = date.today().strftime('%d.%m.%Y')

    # Compact 4-row comparison (newest → older), plus one mid + one old anchor.
    picks = [years[-1], years[-3] if len(years) >= 3 else years[-1],
             years[len(years) // 2], years[0]]
    seen, deduped = set(), []
    for y in picks:
        if y['year'] in seen:
            continue
        seen.add(y['year'])
        deduped.append(y)
    deduped.sort(key=lambda y: y['year'], reverse=True)  # render newest → oldest
    rows = [f"  `{y['year']}` — *${y['median_price']:,}*" for y in deduped]
    table = "\n".join(rows)

    return (
        f"💰 *{name} — HOZIRGI NARX*  ·  {today}\n"
        f"{table}\n"
        f"\n📊 Yangi tahlillar va narxlar: @UzVehiclesMarket\n"
        f"🔎 _O'z mashinangiz narxini bilasizmi?_\n"
        f"👉 @MVehicleBot — 30 soniyada aniq baho\n"
        f"\n━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *{name} — ЦЕНА СЕЙЧАС*  ·  {today}\n"
        f"{table}\n"
        f"\n📊 Свежая аналитика и цены: @UzVehiclesMarket\n"
        f"🔎 _Знаете цену своей машины?_\n"
        f"👉 @MVehicleBot — точная оценка за 30 секунд"
    )


def run(django_url):
    brand, model = _pick()
    entry = fetch(django_url, brand, model)
    if not entry or len(entry.get('years', [])) < 3:
        # Fallback to Cobalt (always has deep data) if the rotated model is thin
        entry = fetch(django_url, 'Chevrolet', 'Cobalt')
    return build_chart(entry), build_text(entry)
