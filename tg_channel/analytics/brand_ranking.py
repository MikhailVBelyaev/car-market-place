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
    brands = data['brands']
    today  = date.today().strftime('%d.%m.%Y')

    uz_lines = [f"  {i+1}. {b['brand']} — {b['count']:,} ta  {pct_arrow(b['pct_change'])}"
                for i, b in enumerate(brands)]
    ru_lines = [f"  {i+1}. {b['brand']} — {b['count']:,} шт  {pct_arrow(b['pct_change'])}"
                for i, b in enumerate(brands)]

    return (
        f"🚗 *ENG KO'P E'LON BERILGAN MARKALAR*\n"
        f"📅 {today}\n\n"
        + "\n".join(uz_lines)
        + f"\n\n💡 _O'z mashinangiz narxini bilmoqchimisiz?_\n"
          f"👉 @MVehicleBot — 30 soniyada bepul baho\n"
          f"\n━━━━━━━━━━━━━━━━━━━━\n\n"
          f"🚗 *САМЫЕ ПОПУЛЯРНЫЕ МАРКИ НЕДЕЛИ*\n"
          f"📅 {today}\n\n"
        + "\n".join(ru_lines)
        + f"\n\n💡 _Узнайте цену своей машины:_\n"
          f"👉 @MVehicleBot — бесплатная оценка за 30 секунд"
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
