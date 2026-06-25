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
    brands  = data['brands']
    today   = date.today().strftime('%d.%m.%Y')
    palette = [BLUE, GREEN, RED]

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=BG)
    apply_base_style(fig, ax)

    for i, b in enumerate(brands):
        months = [m['month'][-5:] for m in b['months']]   # MM-DD style from YYYY-MM
        prices = [m['avg_price']  for m in b['months']]
        if len(months) < 2:
            continue
        color = palette[i % len(palette)]
        ax.plot(range(len(months)), prices, marker='o', color=color, linewidth=2, label=b['brand'])
        ax.fill_between(range(len(months)), prices, alpha=0.1, color=color)

    # x-axis labels from first brand's months
    all_months = data['brands'][0]['months'] if data['brands'] else []
    if all_months:
        step = max(1, len(all_months) // 7)
        ax.set_xticks(range(0, len(all_months), step))
        ax.set_xticklabels(
            [all_months[j]['month'][-5:] for j in range(0, len(all_months), step)],
            fontsize=8)

    ax.set_title(
        f"14 oylik narx tarixi / 14-mesyachnaya istoriya tsen  ·  {today}",
        fontsize=11, fontweight='bold', color='#212121')
    ax.set_ylabel("O'rtacha narq ($) / Srednyaya tsena ($)", fontsize=8.5, color=GREY)
    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${int(x):,}'))

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(data):
    today = date.today().strftime('%d.%m.%Y')
    lines_uz, lines_ru = [], []
    for b in data['brands']:
        months = b['months']
        if len(months) >= 2:
            lo = min(months, key=lambda m: m['avg_price'])
            hi = max(months, key=lambda m: m['avg_price'])
            lines_uz.append(
                f"  {b['brand']}: eng arzon {lo['month']} (${lo['avg_price']:,}), "
                f"eng qimmat {hi['month']} (${hi['avg_price']:,})")
            lines_ru.append(
                f"  {b['brand']}: deshevle vsego {lo['month']} (${lo['avg_price']:,}), "
                f"dorozhe vsego {hi['month']} (${hi['avg_price']:,})")

    return (
        f"\U0001f321 *MAVSUMIIY NARXLAR · {today}*\n\nQachon arzon sotib olish mumkin?\n" +
        '\n'.join(lines_uz) + "\n\n\U0001f449 @MVehicleBot\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"\U0001f321 *SEZONNYE TSENY · {today}*\n\nKogda vygodnee pokupat'?\n" +
        '\n'.join(lines_ru) + "\n\n\U0001f449 @MVehicleBot"
    )


def run(django_url):
    data = fetch(django_url)
    return build_chart(data), build_text(data)
