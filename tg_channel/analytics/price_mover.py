"""Wednesday post: which models rose and fell most in price this week."""
import requests
from datetime import date
from charts.movers import price_movers_chart

DAYS      = 7
MIN_COUNT = 5
TOP       = 5


def fetch(django_url: str) -> dict:
    r = requests.get(
        f"{django_url}/api/cars/price-movers/",
        params={'days': DAYS, 'min_count': MIN_COUNT, 'top': TOP},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _fmt_row(item: dict, lang: str) -> str:
    sign = '+' if item['change_pct'] > 0 else ''
    arrow = '📈' if item['change_pct'] > 0 else '📉'
    if lang == 'uz':
        return (f"  {arrow} *{item['brand']} {item['model']}*  "
                f"{sign}{item['change_pct']:.1f}%  "
                f"(${item['prev_avg_price']:,} → ${item['avg_price']:,})")
    return (f"  {arrow} *{item['brand']} {item['model']}*  "
            f"{sign}{item['change_pct']:.1f}%  "
            f"(${item['prev_avg_price']:,} → ${item['avg_price']:,})")


def build_text(data: dict) -> str:
    risers  = data.get('risers', [])
    fallers = data.get('fallers', [])
    today   = date.today().strftime('%d.%m.%Y')

    rise_uz = "\n".join(_fmt_row(r, 'uz') for r in risers) or "  —"
    fall_uz = "\n".join(_fmt_row(r, 'uz') for r in fallers) or "  —"
    rise_ru = "\n".join(_fmt_row(r, 'ru') for r in risers) or "  —"
    fall_ru = "\n".join(_fmt_row(r, 'ru') for r in fallers) or "  —"

    return (
        f"💹 *HAFTALIK NARX O'ZGARISHLARI*\n"
        f"📅 {today}\n\n"
        f"📈 *Ko'tarildi:*\n{rise_uz}\n\n"
        f"📉 *Tushdi:*\n{fall_uz}\n\n"
        f"💡 _O'z mashinangiz narxini tekshiring:_\n"
        f"👉 @MVehicleBot\n"
        f"\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💹 *ИЗМЕНЕНИЯ ЦЕН ЗА НЕДЕЛЮ*\n"
        f"📅 {today}\n\n"
        f"📈 *Выросли:*\n{rise_ru}\n\n"
        f"📉 *Упали:*\n{fall_ru}\n\n"
        f"💡 _Проверьте цену своей машины:_\n"
        f"👉 @MVehicleBot"
    )


def build_chart(data: dict) -> bytes:
    return price_movers_chart(
        risers=data.get('risers', []),
        fallers=data.get('fallers', []),
        period_days=DAYS,
    )


def run(django_url: str) -> tuple:
    """Returns (chart_buf, caption_text)."""
    data    = fetch(django_url)
    chart   = build_chart(data)
    caption = build_text(data)
    return chart, caption
