"""Monday post: top brands by listing count with week-over-week change."""
import requests
from datetime import date
from charts.bar import brand_ranking_chart
from charts.style import pct_arrow

DAYS = 7
TOP  = 10


def fetch(django_url: str) -> dict:
    r = requests.get(
        f"{django_url}/api/cars/brand-ranking/",
        params={'days': DAYS, 'top': TOP},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def build_text(data: dict) -> str:
    brands = data['brands'][:7]
    today  = date.today().strftime('%d.%m.%Y')
    medal  = ['🥇', '🥈', '🥉']

    # Language-neutral data rows (shared between both blocks) → keeps it dense
    rows = "\n".join(
        f"{medal[i] if i < 3 else f'  {i+1}.'} *{b['brand']}* — {b['count']:,}  {pct_arrow(b['pct_change'])}"
        for i, b in enumerate(brands)
    )

    return (
        f"🚗 *TOP MARKALAR / ТОП МАРОК* · {today}\n"
        f"_e'lonlar soni, hafta / объявлений за неделю_\n\n"
        f"{rows}\n\n"
        f"💡 O'z narxingizni biling / Узнайте свою цену\n"
        f"👉 @MVehicleBot — 30 sek"
    )


def build_chart(data: dict) -> bytes:
    today = date.today().strftime('%d.%m.%Y')
    return brand_ranking_chart(
        brands=data['brands'],
        title=f"Top {TOP} markalar / марок · {today}",
    )


def run(django_url: str) -> tuple:
    """Returns (chart_buf, caption_text)."""
    data    = fetch(django_url)
    chart   = build_chart(data)
    caption = build_text(data)
    return chart, caption
