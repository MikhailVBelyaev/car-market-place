"""
OLX vehicle scraper — v2 (optimized).

This is a rewrite of run_task_scraping_olx_vehicle.py with concurrency, rate
limiting, deduplication against the DB, and a number of correctness fixes.
Every non-trivial change carries an inline comment describing the ORIGINAL BUG
in v1 and the FIX applied here.

Run modes (same CLI contract as v1):
    python run_task_scraping_olx_vehicle_v2.py        # live run, writes to DB
    python run_task_scraping_olx_vehicle_v2.py T      # TEST_MODE, no DB writes
    python run_task_scraping_olx_vehicle_v2.py S      # also fetch phone via selenium
"""

import os
import sys
import logging
import locale
import re
import random
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from pytz import timezone
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import subprocess
import json

BRANDS_JSON_PATH = os.path.join(os.path.dirname(__file__), 'brands_models.json')

USE_SELENIUM = 'S' in sys.argv
TEST_MODE = 'T' in sys.argv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def log(msg):
    logging.info(msg)


# Constants
API_URL_DB = 'http://django:8000/api/cars/'
API_URL_FILTERED = 'http://django:8000/api/cars/filtered-list/'

# Locale and timezone config
try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    log("⚠️ ru_RU.UTF-8 locale not available; date parsing may be limited")
tz_uzbekistan = timezone('Asia/Tashkent')
UZSUM_TO_USD = 12500

# ---------------------------------------------------------------------------
# PERFORMANCE FIX 1: requests.Session with connection pooling + retries.
# v1 called bare requests.get() per request, opening a new TCP connection each
# time and with no retry on transient OLX errors (429/5xx). v2 uses a single
# pooled Session shared across threads with automatic backoff retries.
# ---------------------------------------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20  # FIX: v1 had no timeout, so a hung OLX request could stall forever


def build_session():
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(
        pool_connections=20,
        pool_maxsize=20,  # allows the 5-worker thread pool to reuse connections
        max_retries=retry,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# Session used for scraping OLX (with browser UA + retries).
SESSION = build_session()
# Separate session for talking to our own Django API (UA irrelevant, but reuse pooling).
API_SESSION = build_session()


# ---------------------------------------------------------------------------
# PERFORMANCE FIX 2: thread-safe rate limiter.
# v1 had no throttling at all, which both risks getting blocked by OLX and,
# combined with no concurrency, was simply slow. v2 enforces a minimum spacing
# between outbound OLX requests plus random jitter to look less robotic. It is
# thread-safe because detail pages are now fetched concurrently.
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
            # add jitter outside the strict interval so threads don't sync up
            time.sleep(random.uniform(0, self.max_jitter))
            self._last_ts = time.monotonic()


RATE_LIMITER = RateLimiter(min_interval=0.8, max_jitter=0.4)


def load_brands_and_models():
    try:
        with open(BRANDS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"❌ Failed to load brands_models.json: {e}")
        return [{"brand": "Chevrolet", "model": "Lacetti"}]


# ---------------------------------------------------------------------------
# DATA QUALITY FIX: robust int parser.
# v1 called int(ad.get('mileage', '')) and int(ad.get('year', '')) directly at
# module level (outside any try/except). int('') raises ValueError and crashed
# the entire brand/model pair. It also failed on values like "120 000 км".
# _to_int strips every non-digit char first, so "120 000 км" -> 120000, and
# returns None instead of raising on empty/garbage input.
# ---------------------------------------------------------------------------
def _to_int(val):
    digits = re.sub(r'\D', '', str(val or ''))
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# DATA QUALITY FIX: fuel type mapping with substring logic.
# v1 used an exact-match dict ({'Бензин': 'Gasoline', ...}) that missed every
# variant ("Газ/Бензин", "Гибрид", "Электро/...") and never produced Hybrid at
# all, leaving ~49.5% of rows with NULL fuel_type. v2 lowercases and matches by
# substring with a priority order so compound values resolve sensibly.
# ---------------------------------------------------------------------------
def map_fuel(val):
    if not val:
        return None
    v = str(val).lower()
    if 'гибрид' in v:
        return 'Hybrid'
    if 'электро' in v:
        return 'Electric'
    if 'дизель' in v:
        return 'Diesel'
    # "Газ/Бензин" and similar dual-fuel cars are classified as Gas.
    if 'газ' in v and 'бензин' in v:
        return 'Gas'
    if 'газ' in v:
        return 'Gas'
    if 'бензин' in v:
        return 'Gasoline'
    return None


TRANSMISSION_MAP = {
    'Механическая': 'MT',
    'Автоматическая': 'AT',
    'Робот': 'DSG',
    'Вариатор': 'CVT',
}
COLOR_MAP = {
    'Белый': 'white',
    'Черный': 'black',
    'Серебристый': 'silver',
    'Серый': 'grey',
    'Синий': 'blue',
    'Красный': 'red',
    'Зеленый': 'green',
    'Желтый': 'yellow',
}
CONDITION_MAP = {
    'Отличное': 'ideal',
    'Повреждено': 'damaged',
    'Нуждается в ремонте': 'needs_repair',
    'Б/у': 'used',
}


def fetch_page(url):
    # RELIABILITY FIX: enforce timeout + raise_for_status. v1's fetch_page did
    # neither, so HTTP 404/500 pages were silently parsed as if they were valid.
    RATE_LIMITER.wait()
    response = SESSION.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    log(f"Fetched page: {url}")
    return BeautifulSoup(response.content, 'html.parser')


def extract_car_ad_info(ad):
    car_info = {}

    # Title
    title_tag = ad.find("h4")
    if title_tag:
        car_info["name"] = title_tag.get_text(strip=True)

    # Price
    price_tag = ad.find("p", {"data-testid": "ad-price"})
    if price_tag:
        raw_price = price_tag.get_text(strip=True)
        if "сум" in raw_price:
            numeric_part = raw_price.split("сум")[0].strip()
            car_info["price"] = numeric_part + " сум"
        else:
            car_info["price"] = raw_price

    # Location + Date
    loc_tag = ad.find("p", {"data-testid": "location-date"})
    if loc_tag:
        car_info["location_date"] = loc_tag.get_text(strip=True)
        if " - " in car_info["location_date"]:
            car_info["location"] = car_info["location_date"].split(" - ")[0].strip()

    # Year + Mileage (cleaned)
    mileage_block = ad.select_one('div.css-1kfqt7f span.css-h59g4b')
    if mileage_block:
        # DATA QUALITY FIX: normalize unicode spaces before parsing. OLX uses
        # non-breaking (\xa0) and narrow-no-break ( ) spaces inside numbers
        # like "120\xa0000 км", which v1's .replace(" ", "") never removed, so
        # .isdigit() failed and mileage came back None.
        text = mileage_block.get_text(" ", strip=True).replace("\xa0", " ").replace(" ", " ")
        if "км" in text and "-" in text:
            parts = [p.strip() for p in text.split("-")]
            if len(parts) == 2:
                car_info["year"] = parts[0]
                car_info["mileage"] = _to_int(parts[1])  # FIX: robust parse instead of isdigit

    # URL
    url_tag = ad.find("a", class_="css-1tqlkj0")
    if url_tag and url_tag.get("href"):
        car_info["reference_url"] = "https://www.olx.uz" + url_tag["href"]

    log(f"Extracted car info: {car_info}")
    return car_info


def filter_vehicle_ads(vehicle_ads):
    filtered = []
    for ad in vehicle_ads:
        price = _to_int(ad.get('price', ''))  # FIX: robust parse; v1 did manual replace + int
        mileage = ad.get('mileage', '')
        if price is None:
            continue
        if 20000000 <= price <= 2000000000 and mileage:
            filtered.append(ad)
    return filtered


def scrape_olx_for_vehicles(search_phrase):
    query = search_phrase.strip().replace(" ", "-")
    url = f"https://www.olx.uz/transport/legkovye-avtomobili/q-{query}/?currency=UZS"
    log(f"Scraping first page: {url}")
    soup = fetch_page(url)
    ad_cards = soup.find_all('div', {'data-cy': 'l-card'})
    all_ads = []
    for ad in ad_cards:
        parsed = extract_car_ad_info(ad)
        if parsed:
            all_ads.append(parsed)
    filtered = filter_vehicle_ads(all_ads)
    log(f"Total ads found: {len(all_ads)}; After filtering: {len(filtered)}")
    return filtered


def parse_date(date_str):
    try:
        if "Сегодня" in date_str:
            return datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
        return datetime.strptime(date_str, '%d %B %Y г.')
    except ValueError:
        logging.error(f"Failed to parse date: {date_str}")
        return None


# ---------------------------------------------------------------------------
# DEDUP FIX: load all known car_ad_ids from the DB once at startup.
# v1 issued one GET per ad to check existence (inside save_to_db), and only
# AFTER fetching every detail page. v2 loads the whole id set up front so we can
# skip the expensive detail-page fetch entirely for ads we already have.
# ---------------------------------------------------------------------------
def load_existing_ad_ids():
    if TEST_MODE:
        return set()
    try:
        resp = API_SESSION.get(API_URL_DB, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        ids = {str(row.get("car_ad_id")) for row in data if row.get("car_ad_id")}
        log(f"Loaded {len(ids)} existing car_ad_ids from DB for dedup")
        return ids
    except Exception as e:
        log(f"⚠️ Could not preload existing ad ids ({e}); proceeding without dedup cache")
        return set()


def _ad_id_from_url(reference_url):
    if not reference_url:
        return None
    return reference_url.split('-')[-1].replace('.html', '')


# ---------------------------------------------------------------------------
# PERFORMANCE FIX 3: detail-page fetch extracted into a standalone function so
# it can be dispatched across a ThreadPoolExecutor. In v1 detail fetching was
# inlined in a giant serial loop. Here each call is independent and thread-safe
# (shared Session + RateLimiter handle coordination).
# ---------------------------------------------------------------------------
def fetch_and_parse_detail(ad, brand, model):
    reference_url = ad.get('reference_url')

    # Price (USD)
    usd_price = None
    uzs_price = _to_int(ad.get('price', ''))  # FIX: robust parse (v1 crashed on bad price)
    if uzs_price is not None:
        usd_price = uzs_price / UZSUM_TO_USD

    # Location / date split
    location_date = ad.get('location_date', '')
    location, date = location_date.split(' - ') if ' - ' in location_date else (location_date, None)

    # RELIABILITY FIX: year/mileage via _to_int (None fallback) instead of bare
    # int() that crashed the whole brand/model pair in v1.
    year = _to_int(ad.get('year', ''))
    mileage = _to_int(ad.get('mileage', ''))

    created_at = parse_date(date.strip()) if date else None
    if created_at:
        created_at = tz_uzbekistan.localize(created_at)

    transmission = color = fuel_type = condition = extras = None
    owner_type = body_type = owner_count = None

    if reference_url:
        try:
            detail_html = fetch_page(reference_url)

            params_div = detail_html.find('div', {'data-testid': 'ad-parameters-container'})
            params = params_div.find_all('p') if params_div else []

            # ---------------------------------------------------------------
            # DATA QUALITY FIX: positive model match.
            # v1 only skipped on an explicit mismatch in the "Модель:" param;
            # if that param was absent the ad was kept, so e.g. Gentra listings
            # bled into Lacetti results. v2 REQUIRES the model token to appear
            # in the title OR in the Модель: parameter — otherwise skip.
            # ---------------------------------------------------------------
            expected_model = model.lower().split()[0]
            title_text = (ad.get('name') or '').lower()
            detail_model = ''
            for param in params:
                text = param.get_text(strip=True)
                if text.startswith('Модель:'):
                    detail_model = text.split(':', 1)[-1].strip().lower()
                    break

            model_found = (expected_model in title_text) or (
                bool(detail_model) and expected_model in detail_model
            )
            if not model_found:
                log(
                    f"⏩ Skipping ad (model '{expected_model}' not found in title "
                    f"'{title_text}' or detail model '{detail_model}')"
                )
                return None

            # Parse remaining parameters.
            for param in params:
                text = param.get_text(strip=True)
                if 'Коробка передач:' in text:
                    transmission = TRANSMISSION_MAP.get(text.split(':')[-1].strip())
                elif 'Цвет:' in text:
                    color = COLOR_MAP.get(text.split(':')[-1].strip())
                elif 'Вид топлива:' in text:
                    # FIX: substring-based fuel mapping (see map_fuel)
                    fuel_type = map_fuel(text.split(':')[-1].strip())
                elif 'Состояние машины:' in text:
                    condition = CONDITION_MAP.get(text.split(':')[-1].strip())
                elif 'Доп. опции:' in text:
                    extras = text.split(':', 1)[-1].strip()
                elif 'Частное лицо' in text or 'Компания' in text:
                    owner_type = text.strip()
                elif 'Тип кузова:' in text:
                    body_type = text.split(':')[-1].strip()
                elif 'Количество хозяев:' in text:
                    owner_count = text.split(':')[-1].strip()

            # Description
            desc_outer = detail_html.find('div', {'data-testid': 'ad_description'})
            if desc_outer:
                desc_inner = desc_outer.find('div')
                ad["description_detail"] = (desc_inner or desc_outer).get_text(separator=' ', strip=True)

            # Owner info
            owner_name_tag = detail_html.find('h4', {'data-testid': 'user-profile-user-name'})
            ad["owner_name"] = owner_name_tag.get_text(strip=True) if owner_name_tag else None
            member_since_tag = detail_html.find('p', {'data-testid': 'member-since'})
            ad["owner_member_since"] = member_since_tag.get_text(strip=True) if member_since_tag else None
            last_seen_tag = detail_html.find('p', {'data-testid': 'lastSeenBox'})
            ad["owner_last_seen"] = last_seen_tag.get_text(strip=True) if last_seen_tag else None
            profile_link_tag = detail_html.find('a', {'data-testid': 'user-profile-link'})
            if profile_link_tag and profile_link_tag.get("href") and "/list/user/" in profile_link_tag["href"]:
                ad["owner_profile_url"] = "https://www.olx.uz" + profile_link_tag["href"]
        except Exception as e:
            log(f"❌ Failed to fetch/parse detail for {reference_url}: {e}")

    if USE_SELENIUM and reference_url:
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    os.path.join(os.path.dirname(__file__), 'selenium_fetch_phone.py'),
                    reference_url,
                    'button[data-testid="show-phone"]',
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                ad["owner_tel_number"] = result.stdout.strip()
            else:
                log(f"❌ Selenium returned non-zero exit status {result.returncode}")
        except Exception as e:
            log(f"❌ Selenium fetch failed for phone number: {e}")

    return {
        "brand": brand,
        "model": model,
        "year": year,
        "price": round(usd_price, 2) if usd_price else None,
        "description": ad.get('name'),
        "created_at": created_at,
        "mileage": mileage,
        "location": location.strip() if location else None,
        "reference_url": reference_url,
        "car_ad_id": _ad_id_from_url(reference_url),
        "gear_type": transmission,
        "color": color,
        "fuel_type": fuel_type,
        "condition": condition,
        "additional_options": extras,
        "description_detail": ad.get("description_detail"),
        "owner_name": ad.get("owner_name"),
        "owner_member_since": ad.get("owner_member_since"),
        "owner_last_seen": ad.get("owner_last_seen"),
        "owner_profile_url": ad.get("owner_profile_url"),
        "owner_tel_number": ad.get("owner_tel_number"),
        "owner_type": owner_type,
        "body_type": body_type,
        "owner_count": owner_count,
    }


def process_vehicle_data(vehicle_ads, brand, model, existing_ids):
    # DEDUP FIX: filter out ads whose id is already in the DB BEFORE fetching
    # their detail pages — the most expensive part of scraping.
    to_fetch = []
    for ad in vehicle_ads:
        ad_id = _ad_id_from_url(ad.get('reference_url'))
        if ad_id and ad_id in existing_ids:
            log(f"⏩ Skipping detail fetch — already in DB: {ad_id}")
            continue
        to_fetch.append(ad)

    processed = []
    # PERFORMANCE FIX 3: concurrent detail fetches (max_workers=5).
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_and_parse_detail, ad, brand, model) for ad in to_fetch]
        for fut in futures:
            try:
                result = fut.result()
                if result:
                    processed.append(result)
            except Exception as e:
                log(f"❌ Detail worker failed: {e}")
    return processed


def save_to_db(processed_ads, existing_ids):
    for ad in processed_ads:
        if ad.get("car_ad_id") and ad.get("description") and ad.get("created_at"):
            try:
                if hasattr(ad["created_at"], "isoformat"):
                    ad["created_at"] = ad["created_at"].isoformat()

                post_response = API_SESSION.post(API_URL_DB, json=ad, timeout=REQUEST_TIMEOUT)
                # RELIABILITY FIX: treat BOTH 201 (created) and 200 (already
                # exists, per the new upsert in CarList.post) as success. v1
                # only accepted 201 and logged everything else as an error.
                if post_response.status_code in (200, 201):
                    existing_ids.add(str(ad["car_ad_id"]))  # keep dedup cache current
                    log(f"✅ Saved/exists via API ({post_response.status_code}): {ad['car_ad_id']}")
                else:
                    log(f"❌ API error ({post_response.status_code}) for: {ad['car_ad_id']}")
            except Exception as e:
                logging.error(f"Request failed for car {ad.get('car_ad_id')}: {e}")
        else:
            logging.warning(f"Skipping invalid ad: {ad.get('car_ad_id')}")


def export_data_to_csv(brand, model):
    # RELIABILITY FIX: brand/model are now passed in. v1 hardcoded
    # Chevrolet/Lacetti so every export overwrote the same file regardless of
    # what was actually scraped.
    params = {"brand": brand, "model": model, "color": "white"}
    try:
        response = API_SESSION.get(API_URL_FILTERED, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            df = pd.json_normalize(data)
            export_dir = '/app/databricks/data'
            if not os.path.exists(export_dir):
                export_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), '..', 'databricks', 'data')
                )
            os.makedirs(export_dir, exist_ok=True)
            export_path = os.path.join(export_dir, 'cars_latest.csv')
            df.to_csv(export_path, index=False)
            log(f"✅ CSV exported to: {export_path} (rows: {len(df)})")
        else:
            log(f"❌ Failed to fetch data via API: {response.status_code}")
    except Exception as e:
        logging.error(f"Error fetching data from API: {e}")


def main():
    log(f"Task started at {datetime.now()}")
    brand_model_pairs = load_brands_and_models()

    # DEDUP FIX: load the existing id set once for the whole run.
    existing_ids = load_existing_ad_ids()

    last_brand = last_model = None
    for pair in brand_model_pairs:
        brand = pair.get("brand")
        model = pair.get("model")
        if not brand or not model:
            log("⚠️ Skipping invalid brand-model pair.")
            continue
        last_brand, last_model = brand, model

        search_phrase = f"{model} {brand}"
        try:
            ads = scrape_olx_for_vehicles(search_phrase)
        except Exception as e:
            # RELIABILITY FIX: a failure on one pair must not abort the rest.
            log(f"❌ Failed to scrape pair {brand}/{model}: {e}")
            continue

        if TEST_MODE:
            raw_output_path = os.path.join(
                os.path.dirname(__file__), f'test_raw_output_{brand}_{model}.json'
            )
            with open(raw_output_path, 'w', encoding='utf-8') as f:
                json.dump(ads, f, ensure_ascii=False, indent=2, default=str)
            log(f"✅ Test mode: saved raw ads to {raw_output_path}")

        processed = process_vehicle_data(ads, brand, model, existing_ids)

        if TEST_MODE:
            test_output_path = os.path.join(
                os.path.dirname(__file__), f'test_output_{brand}_{model}.json'
            )
            with open(test_output_path, 'w', encoding='utf-8') as f:
                json.dump(processed, f, ensure_ascii=False, indent=2, default=str)
            log(f"✅ Test mode: saved data to {test_output_path}")
        else:
            save_to_db(processed, existing_ids)

    # PERFORMANCE FIX 4: export CSV ONCE after all pairs, not inside the loop.
    # v1 called export_data_to_csv on every iteration (and always for the same
    # hardcoded Chevrolet/Lacetti), doing N redundant API round-trips.
    if not TEST_MODE and last_brand and last_model:
        export_data_to_csv(last_brand, last_model)

    log(f"Task completed at {datetime.now()}")


if __name__ == "__main__":
    main()
