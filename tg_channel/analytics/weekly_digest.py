"""Friday post: full weekly market digest with brand ranking chart."""
import io
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import date
from charts.style import apply_base_style, BLUE, GREEN, RED, GREY, BG, pct_arrow


def fetch(django_url: str) -> dict:
    r = requests.get(f"{django_url}/api/cars/weekly-digest/", timeout=15)
    r.raise_for_status()
    return r.json()


def build_chart(data: dict) -> io.BytesIO:
    brands = data['top_brands'][:10]
    yoy    = data.get('yoy_price_change', {})
    today  = date.today().strftime('%d.%m.%Y')

    fig = plt.figure(figsize=(12, 9), facecolor=BG)
    gs  = gridspec.GridSpec(2, 1, height_ratios=[1.6, 1], hspace=0.45)

    # ── Top panel: brand ranking bars ──────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    apply_base_style(fig, ax1)

    b_labels = [b['brand'] for b in reversed(brands)]
    b_counts = [b['count'] for b in reversed(brands)]
    colors   = [BLUE] * len(b_labels)

    ax1.barh(b_labels, b_counts, color=colors, height=0.6, zorder=2)
    max_c = max(b_counts) if b_counts else 1
    for i, (brand_data) in enumerate(reversed(brands)):
        ax1.text(
            brand_data['count'] + max_c * 0.01,
            i,
            f"{brand_data['count']:,}   ${brand_data['avg_price']:,}",
            va='center', fontsize=8.5, color='#212121',
        )
    ax1.set_xlim(0, max_c * 1.5)
    ax1.set_title(
        f"Top 10 markalar hafta uchun / марок за неделю  ·  {today}",
        fontsize=11, fontweight='bold', color='#212121', pad=10,
    )
    ax1.set_xlabel("E'lonlar soni / Объявлений", fontsize=8.5, color=GREY)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x):,}'))

    # ── Bottom panel: YoY price changes for top 5 brands ──────────────────
    ax2 = fig.add_subplot(gs[1])
    apply_base_style(fig, ax2)

    yoy_brands  = [b for b in brands[:5] if b['brand'] in yoy]
    yoy_labels  = [b['brand'] for b in yoy_brands]
    yoy_pcts    = [yoy[b['brand']]['change_pct'] for b in yoy_brands]
    bar_colors  = [GREEN if p >= 0 else RED for p in yoy_pcts]

    if yoy_brands:
        bars = ax2.bar(yoy_labels, yoy_pcts, color=bar_colors, width=0.5, zorder=2)
        for bar, pct in zip(bars, yoy_pcts):
            sign = '+' if pct >= 0 else ''
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                pct + (0.3 if pct >= 0 else -0.3),
                f'{sign}{pct:.1f}%',
                ha='center', va='bottom' if pct >= 0 else 'top',
                fontsize=9, fontweight='bold',
                color=GREEN if pct >= 0 else RED,
            )
        ax2.axhline(0, color=GREY, linewidth=1)
        ax2.set_title(
            "1 yillik narx o'zgarishi / Изменение цены за год (%)",
            fontsize=10, fontweight='bold', color='#212121', pad=8,
        )
        ax2.set_ylabel('%', fontsize=9, color=GREY)
    else:
        ax2.text(0.5, 0.5, 'Yillik ma\'lumot yetarli emas',
                 ha='center', va='center', transform=ax2.transAxes,
                 fontsize=10, color=GREY)

    plt.suptitle(
        "📊 Avtomobil bozori | Авторынок Узбекистана",
        fontsize=13, fontweight='bold', color='#212121', y=1.01,
    )

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(data: dict) -> str:
    brands  = data['top_brands']
    total   = data['total_listings']
    prev    = data['prev_total_listings']
    chg     = data.get('total_change_pct')
    yoy     = data.get('yoy_price_change', {})
    today   = date.today().strftime('%d.%m.%Y')

    total_arrow = pct_arrow(chg) if chg is not None else ''

    top3_uz = '\n'.join(
        f"  {i+1}. {b['brand']} — {b['count']:,} ta, o'rtacha ${b['avg_price']:,}"
        for i, b in enumerate(brands[:5])
    )
    top3_ru = '\n'.join(
        f"  {i+1}. {b['brand']} — {b['count']:,} шт, средняя ${b['avg_price']:,}"
        for i, b in enumerate(brands[:5])
    )

    yoy_uz = '\n'.join(
        f"  • {brand}: {pct_arrow(d['change_pct'])} (${d['year_ago']:,} → ${d['now']:,})"
        for brand, d in list(yoy.items())[:4]
    ) or "  Ma'lumot yetarli emas"
    yoy_ru = '\n'.join(
        f"  • {brand}: {pct_arrow(d['change_pct'])} (${d['year_ago']:,} → ${d['now']:,})"
        for brand, d in list(yoy.items())[:4]
    ) or "  Недостаточно данных"

    return (
        f"📊 *HAFTALIK HISOBOT · {today}*\n"
        f"Avtomobil bozori Uzbekiston\n\n"
        f"📋 Jami e'lonlar: *{total:,}* {total_arrow}\n\n"
        f"🏆 *Top 5 markalar:*\n{top3_uz}\n\n"
        f"📉 *1 yillik narx o'zgarishi:*\n{yoy_uz}\n\n"
        f"💡 _O'z mashinangiz qancha turadi?_\n"
        f"👉 @MVehicleBot — 30 soniyada bepul baho\n"
        f"\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 *ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ · {today}*\n"
        f"Авторынок Узбекистана\n\n"
        f"📋 Всего объявлений: *{total:,}* {total_arrow}\n\n"
        f"🏆 *Топ 5 марок:*\n{top3_ru}\n\n"
        f"📉 *Изменение цены за год:*\n{yoy_ru}\n\n"
        f"💡 _Сколько стоит ваша машина сейчас?_\n"
        f"👉 @MVehicleBot — бесплатная оценка за 30 секунд"
    )


def run(django_url: str) -> tuple:
    """Returns (chart_buf, caption_text)."""
    data    = fetch(django_url)
    chart   = build_chart(data)
    caption = build_text(data)
    return chart, caption
