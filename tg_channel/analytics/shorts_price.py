"""Vertical 9:16 "shorts" price card: one model, avg price split by gearbox.

Designed for Stories / Reels / YouTube-Shorts style reposting to drive reach.
Shows last-week median price for Manual vs Automatic with a 10-90 pct range.

Car photo background: if tg_channel/assets/cars/<brand>_<model>.jpg exists it
is used (dimmed) behind the card; otherwise a clean dark gradient is drawn, so
the post always renders even without a photo library.

Model rotates by day-of-year (offset from daily_price so they differ).
"""
import io
import os
from datetime import date, datetime

import numpy as np
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import image as mpimg
from matplotlib.patches import FancyBboxPatch

# Models with reliable weekly volume AND both transmissions (manual + automatic)
# so the manual-vs-automatic split always has two cards to compare.
FEATURED = [
    ('Chevrolet', 'Spark'),   ('Chevrolet', 'Nexia'),
    ('Chevrolet', 'Cobalt'),  ('Chevrolet', 'Lacetti'),
    ('Chevrolet', 'Malibu'),  ('Chevrolet', 'Onix'),
]

INK     = '#0D1B2A'   # deep navy
CARD    = '#152A45'
ACCENT  = '#4FC3F7'   # automatic
ACCENT2 = '#FFB74D'   # manual
WHITE   = '#FFFFFF'
MUTE    = '#9FB3C8'

ASSET_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets', 'cars')


def _pick():
    idx = (datetime.now().timetuple().tm_yday + 4) % len(FEATURED)
    return FEATURED[idx]


def fetch(django_url, brand, model, days=7):
    r = requests.get(
        f"{django_url}/api/cars/analytics/gear-price-split/",
        params={'brand': brand, 'model': model, 'days': days}, timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _find_asset(brand, model):
    """Return the first matching photo for the model, any common extension."""
    stem = f"{brand}_{model}".lower()
    for ext in ('.jpg', '.jpeg', '.png', '.webp'):
        path = os.path.join(ASSET_DIR, stem + ext)
        if os.path.exists(path):
            return path
    return None


CANVAS_ASPECT = 9 / 16   # matches figsize=(9, 16) below — width/height


def _draw_background(ax, brand, model, top=0.97):
    """Dark base + (if available) a dimmed car photo, aspect-correct.

    The photo is "contain"-fit (scaled to preserve its own aspect ratio,
    letterboxed against the dark base) rather than stretched — stretching
    distorts the car. It is anchored near the TOP of the frame (not
    centered) so the header text reads directly on the car, and the price
    cards lower down have room without fully hiding it.
    """
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    ax.imshow(grad, extent=[0, 1, 0, 1], aspect='auto', cmap='cividis',
              alpha=0.55, zorder=0)
    ax.add_patch(plt_rect(0, 0, 1, 1, INK, alpha=0.55, z=1))

    asset = _find_asset(brand, model)
    if not asset:
        return
    try:
        img = mpimg.imread(asset)
    except Exception:
        return

    h, w = img.shape[0], img.shape[1]
    img_aspect = w / h

    if img_aspect > CANVAS_ASPECT:
        # image is relatively wider than the frame → fit to full width,
        # anchor the band near the top instead of centering it
        disp_h = CANVAS_ASPECT / img_aspect
        x0, x1 = 0.0, 1.0
        y1 = top
        y0 = top - disp_h
    else:
        # image is relatively taller than the frame → fit to full height,
        # letterbox left/right (centered — no vertical band to anchor)
        disp_w = img_aspect / CANVAS_ASPECT
        y0, y1 = 0.0, 1.0
        x0 = (1 - disp_w) / 2
        x1 = x0 + disp_w

    faded = _fade_edges(img)
    ax.imshow(faded, extent=[x0, x1, y0, y1], aspect='auto', zorder=1.2)
    overlay = np.zeros((10, 10, 4))
    overlay[..., 3] = 0.62          # black, 62% opacity
    ax.imshow(overlay, extent=[x0, x1, y0, y1], aspect='auto', zorder=1.3)


def _fade_edges(img, frac=0.22):
    """RGBA copy of img with the top/bottom edges feathered to transparent.

    All source photos are landscape catalog shots (aspect 1.5-2.0) being
    letterboxed into a 9:16 frame, so without this the photo band would show
    a hard rectangular seam against the gradient background.
    """
    arr = np.asarray(img, dtype=np.float32)
    if arr.max() > 1.0:
        arr = arr / 255.0
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.ones(arr.shape[:2], dtype=np.float32)])
    else:
        arr = arr.copy()

    fade_px = max(1, int(arr.shape[0] * frac))
    ramp = np.linspace(0, 1, fade_px, dtype=np.float32)
    arr[:fade_px, :, 3]  *= ramp[:, None]
    arr[-fade_px:, :, 3] *= ramp[::-1][:, None]
    return arr


def plt_rect(x, y, w, h, color, alpha=1.0, z=1, radius=0.0):
    return FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        linewidth=0, facecolor=color, alpha=alpha, zorder=z,
        mutation_aspect=0.56,
    )


CARD_H = 0.14


def _card(ax, y, label_uz_ru, median, low, high, color):
    """Price card headlined by the LOW-HIGH range (what buyers actually
    compare against), with the median as a small secondary anchor."""
    ax.add_patch(plt_rect(0.08, y, 0.84, CARD_H, CARD, alpha=0.92, z=3, radius=0.03))
    ax.add_patch(plt_rect(0.08, y, 0.02, CARD_H, color, alpha=1.0, z=4, radius=0.0))
    ax.text(0.14, y + CARD_H * 0.74, label_uz_ru, color=color, fontsize=16.5,
            fontweight='bold', va='center', zorder=5)
    # Escape $ so matplotlib doesn't treat the pair as a mathtext delimiter
    # (that silently drops the $ signs and mixes fonts mid-string).
    ax.text(0.14, y + CARD_H * 0.33, f"\\${low:,} – \\${high:,}", color=WHITE,
            fontsize=25, fontweight='bold', va='center', zorder=5)
    ax.text(0.88, y + CARD_H * 0.33, f"~\\${median:,}", color=MUTE, fontsize=12.5,
            va='center', ha='right', zorder=5)


def build_image(data):
    brand, model = data['brand'], data['model']
    gears = {g['gear']: g for g in data['gears']}
    today = date.today().strftime('%d.%m.%Y')

    fig = plt.figure(figsize=(9, 16), facecolor=INK)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # Photo anchored high (top=0.97) so the header reads on the car, and the
    # cards below (which start well under the photo band) don't bury it.
    _draw_background(ax, brand, model, top=0.97)

    # Header — sits on the car photo
    ax.text(0.5, 0.90, f"{brand.upper()} {model.upper()}", color=WHITE,
            fontsize=34, fontweight='bold', ha='center', zorder=5)
    ax.text(0.5, 0.855, "O'rtacha narx · hafta  |  Средняя цена · неделя",
            color=MUTE, fontsize=15, ha='center', zorder=5)

    # Price cards, pushed down so the car stays visible above them
    mt = gears.get('MT')
    at = gears.get('AT')
    if mt:
        _card(ax, 0.46, "MEXANIKA · МЕХАНИКА", mt['median'], mt['low'], mt['high'], ACCENT2)
    if at:
        _card(ax, 0.29, "AVTOMAT · АВТОМАТ", at['median'], at['low'], at['high'], ACCENT)

    # Footer CTA
    ax.add_patch(plt_rect(0.08, 0.14, 0.84, 0.10, ACCENT, alpha=0.95, z=3, radius=0.03))
    ax.text(0.5, 0.203, "O'z narxingizni biling · Узнайте свою цену",
            color=INK, fontsize=15, fontweight='bold', ha='center', zorder=5)
    ax.text(0.5, 0.165, "@MVehicleBot — 30 sek", color=INK, fontsize=20,
            fontweight='bold', ha='center', zorder=5)
    ax.text(0.5, 0.055, f"OLX.uz · {today}", color=MUTE, fontsize=12,
            ha='center', zorder=5)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, facecolor=INK)  # 1080x1920
    buf.seek(0)
    plt.close(fig)
    return buf


def build_text(data):
    brand, model = data['brand'], data['model']
    gears = {g['gear']: g for g in data['gears']}
    today = date.today().strftime('%d.%m.%Y')
    lines = [f"🚗 *{brand} {model}* — narx / цена · {today}"]
    if gears.get('MT'):
        m = gears['MT']
        lines.append(f"🔧 Mexanika / Механика: *${m['low']:,} – ${m['high']:,}*  (~${m['median']:,})")
    if gears.get('AT'):
        a = gears['AT']
        lines.append(f"⚙️ Avtomat / Автомат: *${a['low']:,} – ${a['high']:,}*  (~${a['median']:,})")
    lines.append("👉 @MVehicleBot — 30 sek")
    return "\n".join(lines)


def run(django_url):
    brand, model = _pick()
    data = fetch(django_url, brand, model)
    if len(data.get('gears', [])) < 1:
        data = fetch(django_url, 'Chevrolet', 'Spark')
    return build_image(data), build_text(data)
