"""Monthly post: how many cars available in each price band."""
import io
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import date
from charts.style import apply_base_style, BLUE, GREEN, RED, GREY, BG


def fetch(django_url):
    r = requests.get(f"{django_url}/api/cars/analytics/market-breadth/", timeout=15)
    r.raise_for_status()
    return r.json()


def build_chart(data):
    bands  = data['bands']
    total  = data['total']
    today  = date.today().strftime('%d.%m.%Y')
    colors_list = [GREEN, BLUE, '#1976D2', '#F57C00', RED]

    fig, ax = plt.subplots(figsize=(9, 6), facecolor=BG)
    apply_base_style(fig, ax)

    labels = [b['label']  for b in bands]
    counts = [b['count']  for b in bands]
    pcts   = [b['pct']    for b in bands]

    bars = ax.bar(labels, counts, color=colors_list[:len(bands)], width=0.6, zorder=2)
    for bar, pct, cnt in zip(bars, pcts, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + total*0.005,
                f"{pct:.0f}%\n({cnt:,})", ha='center', va='bottom', fontsize=8.5, color='#212121')

    ax.set_title(
        f"Narq bo'yicha bozor / Rynok po tsenam  ·  {today}\n"
        f"(Jami / Vsego: {total:,} e'lon / ob'yavleniy)",
        fontsize=10, fontweight='bold', color='#212121')
    ax.set_ylabel("E'lonlar soni / Ob'yavleniy", fontsize=8.5, color=GREY)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x):,}'))
    ax.set_xticklabels(labels, fontsize=8.5)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(data):
    today = date.today().strftime('%d.%m.%Y')
    total = data['total']
    bands = data['bands']
    uz = '\n'.join(f"  {b['label']}: {b['count']:,} ta ({b['pct']:.0f}%)" for b in bands)
    ru = '\n'.join(f"  {b['label']}: {b['count']:,} sht ({b['pct']:.0f}%)" for b in bands)

    return (
        f"\U0001f4e6 *BOZOR TAHLILI · {today}*\nJami: {total:,} ta e'lon\n\n{uz}"
        "\n\n\U0001f449 @MVehicleBot\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"\U0001f4e6 *ANALIZ RYNKA · {today}*\nVsego: {total:,} ob'yavleniy\n\n{ru}"
        "\n\n\U0001f449 @MVehicleBot"
    )


def run(django_url):
    data = fetch(django_url)
    return build_chart(data), build_text(data)
