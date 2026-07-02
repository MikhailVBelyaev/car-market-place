"""Monthly post: 14-month price history — best time to buy."""
import io
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import date
from charts.style import apply_base_style, BLUE, GREEN, RED, GREY, BG


def fetch(django_url):
    r = requests.get(f"{django_url}/api/cars/analytics/seasonal-trends/", timeout=15)
    r.raise_for_status()
    return r.json()


def build_chart(data):
    months_data = data['months']
    label       = f"{data['brand']} {data['model']}"
    today       = date.today().strftime('%d.%m.%Y')

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=BG)
    apply_base_style(fig, ax)

    prices = [m['median_price'] for m in months_data]
    ax.plot(range(len(months_data)), prices, marker='o', color=BLUE, linewidth=2, label=label)
    ax.fill_between(range(len(months_data)), prices, alpha=0.1, color=BLUE)

    # Mark cheapest / priciest month
    if months_data:
        lo = min(range(len(months_data)), key=lambda j: months_data[j]['median_price'])
        hi = max(range(len(months_data)), key=lambda j: months_data[j]['median_price'])
        ax.scatter([lo], [prices[lo]], color=GREEN, s=90, zorder=5)
        ax.scatter([hi], [prices[hi]], color=RED,   s=90, zorder=5)

        step = max(1, len(months_data) // 7)
        ax.set_xticks(range(0, len(months_data), step))
        ax.set_xticklabels(
            [months_data[j]['month'] for j in range(0, len(months_data), step)],
            fontsize=8, rotation=40, ha='right')

    ax.set_title(
        f"{label} · narx bo'yicha oy / tsena po mesyatsam  ·  {today}",
        fontsize=11, fontweight='bold', color='#212121')
    ax.set_ylabel("Mediana narq ($) / Mediannaya tsena ($)", fontsize=8.5, color=GREY)
    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${int(x):,}'))

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(data):
    today = date.today().strftime('%d.%m.%Y')
    label = f"{data['brand']} {data['model']}"
    lo = data.get('cheapest_month')
    hi = data.get('priciest_month')
    if not lo or not hi:
        return f"\U0001f321 *{label}* — ma'lumot yetarli emas / nedostatochno dannyh."

    return (
        f"\U0001f321 *QAYSI OYDA ARZON? · {today}*\n\n"
        f"*{label}* — oylik mediana narx:\n"
        f"  \U0001f7e2 Eng arzon: {lo['month']} — ${lo['median_price']:,}\n"
        f"  \U0001f534 Eng qimmat: {hi['month']} — ${hi['median_price']:,}\n"
        "\n\U0001f449 @MVehicleBot\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"\U0001f321 *В КАКОМ МЕСЯЦЕ ДЕШЕВЛЕ? · {today}*\n\n"
        f"*{label}* — медианная цена по месяцам:\n"
        f"  \U0001f7e2 Дешевле всего: {lo['month']} — ${lo['median_price']:,}\n"
        f"  \U0001f534 Дороже всего: {hi['month']} — ${hi['median_price']:,}\n"
        "\n\U0001f449 @MVehicleBot"
    )


def run(django_url):
    data = fetch(django_url)
    return build_chart(data), build_text(data)
