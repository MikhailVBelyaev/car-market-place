"""
OLX.uz real-estate scraper — apartments + houses.

Follows the same architecture as run_task_scraping_olx_vehicle_v2.py:
  - single pooled requests.Session with automatic backoff retries
  - thread-safe RateLimiter (min interval + jitter) on every OLX request
  - robust int parsing (strip non-digits, never crash on garbage)
  - dedup against the DB up front so we skip detail fetches we already have
  - concurrent detail-page fetches via ThreadPoolExecutor
  - POST to the Django API; both 200 (exists) and 201 (created) are success

Config lives in scrape_apartments_config.json (categories, max_pages, etc).

Run modes (same CLI contract as the vehicle scraper):
    python scrape_apartments.py        # live run, POSTs to Django
    python scrape_apartments.py T      # TEST_MODE, no POST, dumps JSON
"""

import os
import sys
import json
import re
import time
import random
import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'scrape_apartments_config.json')

TEST_MODE = 'T' in sys.argv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def log(msg):
    logging.info(msg)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


CONFIG = load_config()
DJANGO_URL = os.environ.get('DJANGO_URL', CONFIG.get('django_api_url', 'http://django:8000'))
API_URL = f"{DJANGO_URL.rstrip('/')}/api/apartments/"
MAX_RETRIES = CONFIG.get('max_retries', 3)
SLEEP_BETWEEN = CONFIG.get('sleep_between_requests', 1.5)

# ---------------------------------------------------------------------------
# HTTP session with pooling + retries (same pattern as v2 build_session)
# ---------------------------------------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20


def build_session():
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


SESSION = build_session()
API_SESSION = build_session()


# ---------------------------------------------------------------------------
# Thread-safe rate limiter (same as v2). Detail pages are fetched concurrently.
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, min_interval=0.8, max_jitter=0.4):
        self.min_interval = min_interval
        self.max_jitter = max_jitter
        self._lock = threading.Lock()
        self._last_ts = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_ts
            delay = self.min_interval - elapsed
            if delay > 0:
                time.sleep(delay)
            time.sleep(random.uniform(0, self.max_jitter))
            self._last_ts = time.monotonic()


RATE_LIMITER = RateLimiter(min_interval=SLEEP_BETWEEN, max_jitter=0.4)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _to_int(val):
    digits = re.sub(r'\D', '', str(val or ''))
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _to_float(val):
    """Extract the first decimal number from a string ("65,5 м²" -> 65.5)."""
    if val is None:
        return None
    m = re.search(r'\d+(?:[.,]\d+)?', str(val).replace('\xa0', ' '))
    if not m:
        return None
    try:
        return float(m.group(0).replace(',', '.'))
    except ValueError:
        return None


def fetch_page(url):
    RATE_LIMITER.wait()
    response = SESSION.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    log(f"Fetched page: {url}")
    return BeautifulSoup(response.content, 'html.parser')


def _ad_id_from_url(url):
    if not url:
        return None
    return url.split('-')[-1].replace('.html', '').split('?')[0]


def _page_url(base_url, page):
    """Append OLX page param, preserving any existing query string."""
    if page <= 1:
        return base_url
    sep = '&' if '?' in base_url else '?'
    return f"{base_url}{sep}page={page}"


def parse_price(raw_price):
    """Return (numeric_price, currency). OLX shows e.g. '45 000 у.е.' (USD) or
    '550 000 000 сум' (UZS)."""
    if not raw_price:
        return None, None
    low = raw_price.lower()
    if 'сум' in low:
        currency = 'UZS'
    elif 'у.е' in low or 'y.e' in low or '$' in low or 'usd' in low:
        currency = 'USD'
    else:
        currency = None
    return _to_int(raw_price), currency


CONDITION_MAP = {
    'новостройка': 'new',
    'новое': 'new',
    'новый': 'new',
    'требует ремонта': 'old',
    'старый': 'old',
    'вторичка': 'old',
    'дизайнерский ремонт': 'renovation',
    'евроремонт': 'renovation',
    'средний': 'renovation',
    'хорошее': 'renovation',
}


def map_condition(val):
    if not val:
        return None
    v = str(val).lower()
    for key, mapped in CONDITION_MAP.items():
        if key in v:
            return mapped
    return None


# ---------------------------------------------------------------------------
# Listing-card extraction (OLX 'l-card' grid, same selectors as the vehicle
# scraper: data-cy='l-card', data-testid='ad-price', 'location-date', h4 title)
# ---------------------------------------------------------------------------
def extract_card(ad):
    info = {}

    title_tag = ad.find("h4") or ad.find("h6")
    if title_tag:
        info["title"] = title_tag.get_text(strip=True)

    price_tag = ad.find("p", {"data-testid": "ad-price"})
    if price_tag:
        info["price_raw"] = price_tag.get_text(strip=True)

    loc_tag = ad.find("p", {"data-testid": "location-date"})
    if loc_tag:
        loc_date = loc_tag.get_text(strip=True)
        info["location_date"] = loc_date
        if " - " in loc_date:
            info["district"] = loc_date.split(" - ")[0].strip()

    url_tag = ad.find("a", class_="css-1tqlkj0") or ad.find("a", href=True)
    if url_tag and url_tag.get("href"):
        href = url_tag["href"]
        if href.startswith("/"):
            href = "https://www.olx.uz" + href
        info["url"] = href

    return info


# ---------------------------------------------------------------------------
# Detail-page parsing — pulls structured params from the ad page.
# ---------------------------------------------------------------------------
def parse_detail(detail_html, info):
    out = dict(info)

    price, currency = parse_price(info.get("price_raw"))
    out["price"] = price
    out["price_currency"] = currency

    area = rooms = floor = total_floors = None
    condition = property_type = None

    params_div = detail_html.find('div', {'data-testid': 'ad-parameters-container'})
    params = params_div.find_all('p') if params_div else []
    for param in params:
        text = param.get_text(" ", strip=True)
        low = text.lower()
        if 'количество комнат' in low or low.startswith('комнат'):
            rooms = _to_int(text)
        elif 'общая площадь' in low or ('площадь' in low and area is None):
            area = _to_float(text)
        elif 'этажность дома' in low or 'этажей в доме' in low:
            total_floors = _to_int(text)
        elif 'этаж' in low and floor is None:
            floor = _to_int(text)
        elif 'ремонт' in low or 'состояние' in low:
            condition = map_condition(text)
        elif 'тип жилья' in low or 'тип дома' in low:
            property_type = text.split(':')[-1].strip()

    # Fallback: derive m2 from the title (e.g. "3-комн. квартира, 75 м²")
    if area is None and info.get("title"):
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*м', info["title"])
        if m:
            area = _to_float(m.group(1))
    if rooms is None and info.get("title"):
        m = re.search(r'(\d+)\s*-?\s*комн', info["title"].lower())
        if m:
            rooms = _to_int(m.group(1))

    out["area_m2"] = area
    out["rooms"] = rooms
    out["floor"] = floor
    out["total_floors"] = total_floors
    out["condition"] = condition
    out["property_type"] = property_type

    # Description
    desc_outer = detail_html.find('div', {'data-testid': 'ad_description'})
    if desc_outer:
        desc_inner = desc_outer.find('div')
        out["description"] = (desc_inner or desc_outer).get_text(separator=' ', strip=True)

    # Address (location map block)
    addr_tag = detail_html.find('p', {'data-testid': 'location-name'})
    if addr_tag:
        out["address"] = addr_tag.get_text(strip=True)

    # Seller
    seller_tag = detail_html.find('h4', {'data-testid': 'user-profile-user-name'})
    out["seller_name"] = seller_tag.get_text(strip=True) if seller_tag else None

    # Images
    images = []
    gallery = detail_html.find_all('img', {'data-testid': 'swiper-image'})
    for img in gallery:
        src = img.get('src') or img.get('data-src')
        if src:
            images.append(src)
    out["images"] = images or None

    return out


def build_record(detail, category_name):
    """Map parsed detail dict to the Apartment API payload."""
    url = detail.get("url")
    property_type = detail.get("property_type")
    if not property_type:
        property_type = 'house' if category_name == 'houses' else 'apartment'
    return {
        "ad_id": _ad_id_from_url(url),
        "title": detail.get("title"),
        "price": detail.get("price"),
        "price_currency": detail.get("price_currency"),
        "area_m2": detail.get("area_m2"),
        "rooms": detail.get("rooms"),
        "floor": detail.get("floor"),
        "total_floors": detail.get("total_floors"),
        "district": detail.get("district"),
        "address": detail.get("address"),
        "condition": detail.get("condition"),
        "property_type": property_type,
        "description": detail.get("description"),
        "seller_name": detail.get("seller_name"),
        "seller_phone": detail.get("seller_phone"),
        "url": url,
        "images": detail.get("images"),
        "created_at": datetime.now().isoformat(),
        "scraped_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Dedup + persistence
# ---------------------------------------------------------------------------
def load_existing_ad_ids():
    if TEST_MODE:
        return set()
    try:
        resp = API_SESSION.get(API_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        ids = {str(row.get("ad_id")) for row in data if row.get("ad_id")}
        log(f"Loaded {len(ids)} existing apartment ad_ids from DB for dedup")
        return ids
    except Exception as e:
        log(f"⚠️ Could not preload existing ad ids ({e}); proceeding without dedup cache")
        return set()


def fetch_and_build(card, category_name):
    url = card.get("url")
    if not url:
        return None
    try:
        detail_html = fetch_page(url)
        detail = parse_detail(detail_html, card)
        return build_record(detail, category_name)
    except Exception as e:
        log(f"❌ Failed to fetch/parse detail for {url}: {e}")
        return None


def save_to_db(records, existing_ids):
    for rec in records:
        if not rec.get("ad_id"):
            log("⚠️ Skipping record with no ad_id")
            continue
        try:
            resp = API_SESSION.post(API_URL, json=rec, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (200, 201):
                existing_ids.add(str(rec["ad_id"]))
                log(f"✅ Saved/exists via API ({resp.status_code}): {rec['ad_id']}")
            else:
                log(f"❌ API error ({resp.status_code}) for {rec['ad_id']}: {resp.text[:200]}")
        except Exception as e:
            logging.error(f"Request failed for apartment {rec.get('ad_id')}: {e}")


# ---------------------------------------------------------------------------
# Main scrape loop
# ---------------------------------------------------------------------------
def scrape_category(category, existing_ids):
    name = category["name"]
    base_url = category["url"]
    max_pages = category.get("max_pages", 1)

    all_records = []
    for page in range(1, max_pages + 1):
        url = _page_url(base_url, page)
        try:
            soup = fetch_page(url)
        except Exception as e:
            log(f"❌ Failed to fetch listing page {url}: {e}")
            break

        cards = soup.find_all('div', {'data-cy': 'l-card'})
        if not cards:
            log(f"No cards on page {page} of {name}; stopping pagination")
            break

        parsed_cards = [extract_card(c) for c in cards]

        # Dedup BEFORE the expensive detail fetch (same as v2 process step).
        to_fetch = []
        for card in parsed_cards:
            ad_id = _ad_id_from_url(card.get("url"))
            if ad_id and ad_id in existing_ids:
                log(f"⏩ Skipping detail fetch — already in DB: {ad_id}")
                continue
            to_fetch.append(card)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_and_build, c, name) for c in to_fetch]
            for fut in futures:
                try:
                    rec = fut.result()
                    if rec:
                        all_records.append(rec)
                except Exception as e:
                    log(f"❌ Detail worker failed: {e}")

        log(f"[{name}] page {page}: {len(cards)} cards, {len(to_fetch)} new fetched")

    return all_records


def main():
    log(f"Apartment scrape started at {datetime.now()} (API: {API_URL})")
    existing_ids = load_existing_ad_ids()

    for category in CONFIG["categories"]:
        try:
            records = scrape_category(category, existing_ids)
        except Exception as e:
            log(f"❌ Failed to scrape category {category.get('name')}: {e}")
            continue

        if TEST_MODE:
            out_path = os.path.join(
                os.path.dirname(__file__), f"test_apartments_{category['name']}.json"
            )
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2, default=str)
            log(f"✅ Test mode: saved {len(records)} records to {out_path}")
        else:
            save_to_db(records, existing_ids)

    log(f"Apartment scrape completed at {datetime.now()}")


if __name__ == "__main__":
    main()
