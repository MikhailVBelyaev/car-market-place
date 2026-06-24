"""Friday post: full weekly market digest — brands + top models with price ranges."""
import io
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from datetime import date
from charts.style import apply_base_style, BLUE, GREEN, RED, GREY, BG, pct_arrow


def fetch(django_url: str) -> dict:
    r = requests.get(f"{django_url}/api/cars/weekly-digest/", timeout=15)
    r.raise_for_status()
    return r.json()


def build_chart(data: dict) -> io.BytesIO:
    brands = data['top_brands'][:8]
    today  = date.today().strftime('%d.%m.%Y')

    fig = plt.figure(figsize=(13, 10), facecolor=BG)
    gs  = gridspec.GridSpec(2, 1, height_ratios=[1.4, 1], hspace=0.5)

    # ── Top panel: brand bars ──────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    apply_base_style(fig, ax1)

    b_labels = [b['brand'] for b in reversed(brands)]
    b_counts = [b['count'] for b in reversed(brands)]
    ax1.barh(b_labels, b_counts, color=BLUE, height=0.6, zorder=2)
    max_c = max(b_counts) if b_counts else 1
    for i, b in enumerate(reversed(brands)):
        ax1.text(
            b['count'] + max_c * 0.01, i,
            f"{b['count']:,}   avg ${b['avg_price']:,}",
            va='center', fontsize=8.5, color='#212121',
        )
    ax1.set_xlim(0, max_c * 1.55)
    ax1.set_title(
        f"Top markalar hafta uchun / Топ марок за неделю  ·  {today}",
        fontsize=11, fontweight='bold', color='#212121', pad=10,
    )
    ax1.set_xlabel("E'lonlar soni / Объявлений", fontsize=8.5, color=GREY)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x):,}'))

    # ── Bottom panel: top 3 brands × top 3 models price range ─────────────────
    ax2 = fig.add_subplot(gs[1])
    apply_base_style(fig, ax2)

    top3_brands = [b for b in brands[:3] if b.get('models')]
    if top3_brands:
        labels, mins_list, maxs_list, avgs_list, colors_list = [], [], [], [], []
        palette = [BLUE, '#1976D2', '#42A5F5']
        for ci, brand in enumerate(top3_brands):
            for m in brand['models'][:3]:
                labels.append(f"{m['model'][:10]}\n({brand['brand'][:6]})")
                mins_list.append(m['min_price'])
                maxs_list.append(m['max_price'])
                avgs_list.append(m['avg_price'])
                colors_list.append(palette[ci % len(palette)])

        y = np.arange(len(labels))
        ranges = [mx - mn for mn, mx in zip(mins_list, maxs_list)]
        ax2.barh(y, ranges, left=mins_list, color=colors_list, height=0.5, alpha=0.55, zorder=2)
        ax2.scatter(avgs_list, y, color=colors_list, s=40, zorder=3, label='avg')

        for i, (mn, mx, av) in enumerate(zip(mins_list, maxs_list, avgs_list)):
            ax2.text(mx + (max(maxs_list) - min(mins_list)) * 0.01, i,
                     f"avg ${av:,}", va='center', fontsize=7.5, color='#212121')

        ax2.set_yticks(y)
        ax2.set_yticklabels(labels, fontsize=8)
        ax2.set_title(
            "Modellar narx diapazoni / Диапазон цен по моделям ($)",
            fontsize=10, fontweight='bold', color='#212121', pad=8,
        )
        ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${int(x):,}'))
    else:
        ax2.text(0.5, 0.5, "Ma'lumot yetarli emas",
                 ha='center', va='center', transform=ax2.transAxes, fontsize=10, color=GREY)

    plt.suptitle(
        "📊 Avtomobil bozori | Авторынок Узбекистана",
        fontsize=13, fontweight='bold', color='#212121', y=1.01,
    )

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def _model_line(m: dict, lang: str) -> str:
    """One line per model: name, count, price range, avg, YoY change."""
    count_word = "ta" if lang == 'uz' else "шт"
    avg_word   = "avg" if lang == 'uz' else "avg"
    line = f"   • {m['model']}: {m['count']:,} {count_word} · ${m['min_price']:,}–${m['max_price']:,} · {avg_word} ${m['avg_price']:,}"
    if m.get('yoy_pct') is not None:
        arrow = pct_arrow(m['yoy_pct'])
        line += f" · {arrow}"
    return line


def build_text(data: dict) -> str:
    brands = data['top_brands']
    total  = data['total_listings']
    today  = date.today().strftime('%d.%m.%Y')

    # Build brand blocks (top 5 brands, top 5 models each)
    uz_blocks, ru_blocks = [], []
    for b in brands[:5]:
        uz_lines = [f"🚗 *{b['brand']}* — {b['count']:,} ta e'lon"]
        ru_lines = [f"🚗 *{b['brand']}* — {b['count']:,} шт"]
        for m in b.get('models', [])[:5]:
            uz_lines.append(_model_line(m, 'uz'))
            ru_lines.append(_model_line(m, 'ru'))
        uz_blocks.append('\n'.join(uz_lines))
        ru_blocks.append('\n'.join(ru_lines))

    uz_brands_text = '\n\n'.join(uz_blocks)
    ru_brands_text = '\n\n'.join(ru_blocks)

    return (
        f"📊 *HAFTALIK HISOBOT · {today}*\n"
        f"Avtomobil bozori Uzbekiston\n\n"
        f"📋 Jami e'lonlar: *{total:,}*\n\n"
        f"🏆 *Top 5 markalar va eng mashhur modellar:*\n\n"
        f"{uz_brands_text}\n\n"
        f"💡 _O'z mashinangiz qancha turadi?_\n"
        f"👉 @MVehicleBot — 30 soniyada bepul baho\n"
        f"\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 *ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ · {today}*\n"
        f"Авторынок Узбекистана\n\n"
        f"📋 Всего объявлений: *{total:,}*\n\n"
        f"🏆 *Топ 5 марок и самые популярные модели:*\n\n"
        f"{ru_brands_text}\n\n"
        f"💡 _Сколько стоит ваша машина сейчас?_\n"
        f"👉 @MVehicleBot — бесплатная оценка за 30 секунд"
    )


def run(django_url: str) -> tuple:
    """Returns (chart_buf, caption_text)."""
    data    = fetch(django_url)
    chart   = build_chart(data)
    caption = build_text(data)
    return chart, caption
