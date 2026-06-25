"""Monthly post: how car value drops by year of manufacture."""
import io
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import date
from charts.style import apply_base_style, BLUE, GREEN, RED, GREY, BG


def fetch(django_url):
    r = requests.get(f"{django_url}/api/cars/analytics/age-depreciation/", timeout=15)
    r.raise_for_status()
    return r.json()


def build_chart(data):
    brands = data['brands']
    today  = date.today().strftime('%d.%m.%Y')
    palette = [BLUE, GREEN, RED]

    fig, ax = plt.subplots(figsize=(11, 6), facecolor=BG)
    apply_base_style(fig, ax)

    for i, b in enumerate(brands):
        years  = [y['year']      for y in b['years']]
        prices = [y['avg_price'] for y in b['years']]
        color  = palette[i % len(palette)]
        ax.plot(years, prices, marker='o', color=color, linewidth=2, label=b['brand'])
        if prices:
            ax.annotate(f"${prices[-1]:,}", (years[-1], prices[-1]),
                        textcoords="offset points", xytext=(6, 0),
                        fontsize=8, color=color)

    ax.set_title(
        f"Yil bo'yicha narx / Tseny po godu vypuska  ·  {today}",
        fontsize=11, fontweight='bold', color='#212121')
    ax.set_xlabel("Ishlab chiqarilgan yil / God vypuska", fontsize=8.5, color=GREY)
    ax.set_ylabel("O'rtacha narq / Srednyaya tsena ($)", fontsize=8.5, color=GREY)
    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${int(x):,}'))

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(data):
    today  = date.today().strftime('%d.%m.%Y')
    lines_uz, lines_ru = [], []
    for b in data['brands']:
        years = b['years']
        if len(years) >= 2:
            oldest = years[0]
            newest = years[-1]
            drop   = round((oldest['avg_price'] - newest['avg_price']) / newest['avg_price'] * 100)
            lines_uz.append(
                f"  {b['brand']}: {oldest['year']} ${oldest['avg_price']:,} → "
                f"{newest['year']} ${newest['avg_price']:,} (+{drop}% yangi)")
            lines_ru.append(
                f"  {b['brand']}: {oldest['year']} ${oldest['avg_price']:,} → "
                f"{newest['year']} ${newest['avg_price']:,} (+{drop}% novee)")

    return (
        f"📅 *YIL BO'YICHA NARX · {today}*\n\n"
        f"Yangi mashina qancha qimmatroq?\n" + '\n'.join(lines_uz) +
        "\n\n\U0001f449 @MVehicleBot\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 *TSENY PO GODU VYPUSKA · {today}*\n\n"
        f"Naskol'ko novee = dorozhe?\n" + '\n'.join(lines_ru) +
        "\n\n\U0001f449 @MVehicleBot"
    )


def run(django_url):
    data = fetch(django_url)
    return build_chart(data), build_text(data)
