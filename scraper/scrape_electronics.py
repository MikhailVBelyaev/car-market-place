"""
OLX.uz electronics scraper — video cards (GPUs) + Apple products.

Same architecture as run_task_scraping_olx_vehicle_v2.py:
  - pooled requests.Session with backoff retries
  - thread-safe RateLimiter (min interval + jitter)
  - robust int parsing, dedup against the DB, concurrent detail fetches
  - POST to the Django API; 200 (exists) and 201 (created) both = success

Each category writes a JSONB `specs` blob tailored to its kind:
  gpu     -> {"memory_gb", "gpu_series"}
  iphone  -> {"storage_gb", "color"}
  macbook -> {"ram_gb", "storage_gb", "chip"}
  ipad    -> {"storage_gb", "color"}

Config lives in scrape_electronics_config.json.

Run modes:
    python scrape_electronics.py        # live run, POSTs to Django
    python scrape_electronics.py T      # TEST_MODE, no POST, dumps JSON
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

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'scrape_electronics_config.json')

TEST_MODE = 'T' in sys.argv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def log(msg):
    logging.info(msg)


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


CONFIG = load_config()
DJANGO_URL = os.environ.get('DJANGO_URL', CONFIG.get('django_api_url', 'http://django:8000'))
API_URL = f"{DJANGO_URL.rstrip('/')}/api/electronics/"
MAX_RETRIES = CONFIG.get('max_retries', 3)
SLEEP_BETWEEN = CONFIG.get('sleep_between_requests', 1.5)

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
# Helpers
# ---------------------------------------------------------------------------
def _to_int(val):
    digits = re.sub(r'\D', '', str(val or ''))
    if not digits:
        return None
    try:
        return int(digits)
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
    if page <= 1:
        return base_url
    sep = '&' if '?' in base_url else '?'
    return f"{base_url}{sep}page={page}"


def parse_price(raw_price):
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


CONDITION_TOKENS = {
    'новый': 'new',
    'новое': 'new',
    'new': 'new',
    'б/у': 'used',
    'бу': 'used',
    'used': 'used',
    'подержанный': 'used',
}


def map_condition(val):
    if not val:
        return None
    v = str(val).lower()
    for token, mapped in CONDITION_TOKENS.items():
        if token in v:
            return mapped
    return None


# ---------------------------------------------------------------------------
# Category / brand / model / spec parsing from the title
# ---------------------------------------------------------------------------
def detect_category(category_name, title):
    """Prefer the configured category; fall back to keyword detection in title."""
    t = (title or '').lower()
    if category_name in ('gpu', 'iphone', 'macbook', 'ipad'):
        return category_name
    if 'airpods' in t:
        return 'airpods'
    if 'macbook' in t:
        return 'macbook'
    if 'ipad' in t:
        return 'ipad'
    if 'iphone' in t:
        return 'iphone'
    if any(k in t for k in ('видеокарт', 'rtx', 'gtx', 'radeon', 'geforce', 'rx ')):
        return 'gpu'
    return category_name


def parse_brand_model(category, title):
    """Return (brand, model) parsed from the listing title."""
    t = title or ''
    low = t.lower()

    if category in ('iphone', 'macbook', 'ipad', 'airpods'):
        brand = 'Apple'
        if category == 'iphone':
            m = re.search(r'iphone\s*(\d+\s*(?:pro\s*max|pro|plus|mini|se)?)', low)
            model = ('iPhone ' + m.group(1).strip().title()) if m else 'iPhone'
        elif category == 'macbook':
            m = re.search(r'macbook\s*(air|pro)?\s*(m[1-4](?:\s*(?:pro|max|ultra))?)?', low)
            parts = ['MacBook']
            if m:
                if m.group(1):
                    parts.append(m.group(1).title())
                if m.group(2):
                    parts.append(m.group(2).upper().replace(' ', ' '))
            model = ' '.join(parts)
        elif category == 'ipad':
            m = re.search(r'ipad\s*(air|pro|mini)?\s*(\d+)?', low)
            parts = ['iPad']
            if m:
                if m.group(1):
                    parts.append(m.group(1).title())
                if m.group(2):
                    parts.append(m.group(2))
            model = ' '.join(parts)
        else:
            model = 'AirPods'
        return brand, model

    # GPU: brand = chip maker, model = the card series in the title
    if 'rtx' in low or 'gtx' in low or 'geforce' in low or 'nvidia' in low:
        brand = 'NVIDIA'
    elif 'radeon' in low or re.search(r'\brx\s*\d', low) or 'amd' in low:
        brand = 'AMD'
    else:
        brand = None
    m = re.search(r'((?:rtx|gtx|rx)\s*\d{3,4}\s*(?:ti|super|xt)?)', low)
    model = m.group(1).upper().strip() if m else None
    return brand, model


def parse_specs(category, title, params_text):
    """Build the per-category JSONB specs blob from title + detail params."""
    text = f"{title or ''} {params_text or ''}"
    low = text.lower()
    specs = {}

    if category == 'gpu':
        m = re.search(r'(\d+)\s*(?:gb|гб)', low)
        if m:
            specs['memory_gb'] = _to_int(m.group(1))
        s = re.search(r'((?:rtx|gtx|rx)\s*\d{3,4}\s*(?:ti|super|xt)?)', low)
        if s:
            specs['gpu_series'] = s.group(1).upper().strip()

    elif category in ('iphone', 'ipad'):
        m = re.search(r'(\d+)\s*(?:gb|гб|tb|тб)', low)
        if m:
            val = _to_int(m.group(1))
            # interpret TB as GB
            if 'tb' in low or 'тб' in low:
                val = (val or 0) * 1024
            specs['storage_gb'] = val
        for color in ('black', 'white', 'blue', 'green', 'red', 'gold', 'silver',
                      'purple', 'pink', 'graphite', 'titanium',
                      'черный', 'белый', 'синий', 'зеленый', 'красный', 'золотой', 'серый'):
            if color in low:
                specs['color'] = color
                break

    elif category == 'macbook':
        ram = re.search(r'(\d+)\s*(?:gb|гб)\s*(?:ram|озу|память)?', low)
        if ram:
            specs['ram_gb'] = _to_int(ram.group(1))
        storage = re.search(r'(\d+)\s*(?:gb|гб|tb|тб)\s*(?:ssd|накопит|памят)', low)
        if storage:
            val = _to_int(storage.group(1))
            if 'tb' in storage.group(0) or 'тб' in storage.group(0):
                val = (val or 0) * 1024
            specs['storage_gb'] = val
        chip = re.search(r'(m[1-4](?:\s*(?:pro|max|ultra))?)', low)
        if chip:
            specs['chip'] = chip.group(1).upper().strip()

    return specs or None


# ---------------------------------------------------------------------------
# Card + detail extraction
# ---------------------------------------------------------------------------
def extract_card(ad):
    info = {}
    title_tag = ad.find("h4") or ad.find("h6")
    if title_tag:
        info["title"] = title_tag.get_text(strip=True)

    price_tag = ad.find("p", {"data-testid": "ad-price"})
    if price_tag:
        info["price_raw"] = price_tag.get_text(strip=True)

    url_tag = ad.find("a", class_="css-1tqlkj0") or ad.find("a", href=True)
    if url_tag and url_tag.get("href"):
        href = url_tag["href"]
        if href.startswith("/"):
            href = "https://www.olx.uz" + href
        info["url"] = href

    return info


def parse_detail(detail_html, card, category_name):
    info = dict(card)
    title = info.get("title", "")

    category = detect_category(category_name, title)

    price, currency = parse_price(info.get("price_raw"))

    params_div = detail_html.find('div', {'data-testid': 'ad-parameters-container'})
    params = params_div.find_all('p') if params_div else []
    params_text = ' '.join(p.get_text(" ", strip=True) for p in params)

    condition = None
    for param in params:
        text = param.get_text(" ", strip=True)
        if 'состояние' in text.lower():
            condition = map_condition(text)
            break
    if condition is None:
        condition = map_condition(title) or map_condition(params_text)

    brand, model = parse_brand_model(category, title)
    specs = parse_specs(category, title, params_text)

    description = None
    desc_outer = detail_html.find('div', {'data-testid': 'ad_description'})
    if desc_outer:
        desc_inner = desc_outer.find('div')
        description = (desc_inner or desc_outer).get_text(separator=' ', strip=True)

    seller_tag = detail_html.find('h4', {'data-testid': 'user-profile-user-name'})
    seller_name = seller_tag.get_text(strip=True) if seller_tag else None

    images = []
    for img in detail_html.find_all('img', {'data-testid': 'swiper-image'}):
        src = img.get('src') or img.get('data-src')
        if src:
            images.append(src)

    url = info.get("url")
    return {
        "ad_id": _ad_id_from_url(url),
        "category": category,
        "title": title,
        "brand": brand,
        "model": model,
        "price": price,
        "price_currency": currency,
        "condition": condition,
        "description": description,
        "seller_name": seller_name,
        "seller_phone": None,
        "url": url,
        "images": images or None,
        "specs": specs,
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
        log(f"Loaded {len(ids)} existing electronics ad_ids from DB for dedup")
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
        return parse_detail(detail_html, card, category_name)
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
            logging.error(f"Request failed for electronics {rec.get('ad_id')}: {e}")


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
    log(f"Electronics scrape started at {datetime.now()} (API: {API_URL})")
    existing_ids = load_existing_ad_ids()

    for category in CONFIG["categories"]:
        try:
            records = scrape_category(category, existing_ids)
        except Exception as e:
            log(f"❌ Failed to scrape category {category.get('name')}: {e}")
            continue

        if TEST_MODE:
            out_path = os.path.join(
                os.path.dirname(__file__), f"test_electronics_{category['name']}.json"
            )
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2, default=str)
            log(f"✅ Test mode: saved {len(records)} records to {out_path}")
        else:
            save_to_db(records, existing_ids)

    log(f"Electronics scrape completed at {datetime.now()}")


if __name__ == "__main__":
    main()
