"""Weekly post: listings priced below market (buy signals)."""
import io
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import date
from charts.style import apply_base_style, BLUE, GREEN, RED, GREY, BG


def fetch(django_url):
    r = requests.get(f"{django_url}/api/cars/analytics/best-value/", timeout=15)
    r.raise_for_status()
    return r.json()


def build_chart(data):
    listings = data['listings'][:8]
    today    = date.today().strftime('%d.%m.%Y')

    fig, ax = plt.subplots(figsize=(11, 6), facecolor=BG)
    apply_base_style(fig, ax)

    labels    = [f"{l['brand']} {l['model']}\n{l['year']} · {l['mileage']//1000}k km" for l in listings]
    prices    = [l['price']         for l in listings]
    medians   = [l['median_price']  for l in listings]
    y         = list(range(len(labels)))

    ax.barh(y, medians, color=GREY,  height=0.5, alpha=0.4, label="Market median (same km band)", zorder=2)
    ax.barh(y, prices,  color=GREEN, height=0.5, label="Listed price",                             zorder=3)

    for i, l in enumerate(listings):
        ax.text(l['median_price'] + 100, i, f"-{l['discount_pct']:.0f}%",
                va='center', fontsize=8.5, color=RED, fontweight='bold')

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_title(f"Bozordan arzon · Nizhe rynka  ·  {today}", fontsize=11, fontweight='bold', color='#212121')
    ax.set_xlabel("Narq / Tsena ($)", fontsize=8.5, color=GREY)
    ax.legend(fontsize=9)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${int(x):,}'))

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(data):
    today    = date.today().strftime('%d.%m.%Y')
    listings = data['listings']

    uz_lines = '\n'.join(
        f"  \U0001f49a {l['brand']} {l['model']} {l['year']} ({l['mileage']//1000}k km): ${l['price']:,} "
        f"(bozor mediana ${l['median_price']:,}, -{l['discount_pct']:.0f}%)"
        for l in listings[:5])
    ru_lines = '\n'.join(
        f"  \U0001f49a {l['brand']} {l['model']} {l['year']} ({l['mileage']//1000}k km): ${l['price']:,} "
        f"(rynok mediana ${l['median_price']:,}, -{l['discount_pct']:.0f}%)"
        for l in listings[:5])

    return (
        f"\U0001f48e *ARZON TAKLIFLAR · {today}*\n\nBu hafta bozordan arzon mashinalar:\n{uz_lines}"
        "\n\n\U0001f4a1 _Narqni tekshirish:_ \U0001f449 @MVehicleBot\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"\U0001f48e *VYGODNYE PREDLOZHENIYA · {today}*\n\nMashiny nizhe rynka na etoy nedele:\n{ru_lines}"
        "\n\n\U0001f4a1 _Proverit' tsenu:_ \U0001f449 @MVehicleBot"
    )


def run(django_url):
    data = fetch(django_url)
    return build_chart(data), build_text(data)
