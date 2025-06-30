import os
import sys
import logging
import locale
from datetime import datetime
from pytz import timezone
import pandas as pd
import requests
from bs4 import BeautifulSoup
import subprocess
import json

BRANDS_JSON_PATH = os.path.join(os.path.dirname(__file__), 'brands_models.json')

USE_SELENIUM = 'S' in sys.argv
TEST_MODE = 'T' in sys.argv

# Configure logging and printing
# Configure logging once
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # prints to terminal & container logs
    ]
)
def log(msg): 
    logging.info(msg)

# Constants
API_URL_DB = 'http://django:8000/api/cars/'
API_URL_FILTERED = 'http://django:8000/api/cars/filtered-list/'


def load_brands_and_models():
    try:
        with open(BRANDS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"❌ Failed to load brands_models.json: {e}")
        return [{"brand": "Chevrolet", "model": "Lacetti"}]

# Locale and timezone config
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
tz_uzbekistan = timezone('Asia/Tashkent')
UZSUM_TO_USD = 12500

def fetch_page(url):
    response = requests.get(url)
    log(f"Fetched page: {url}")
    return BeautifulSoup(response.content, 'html.parser')

def extract_car_ad_info(ad):
    car_info = {}
    title = ad.find('h4', class_='css-1g61gc2')
    if title: car_info['name'] = title.get_text(strip=True)
    price = ad.find('p', {'data-testid': 'ad-price'})
    if price: car_info['price'] = price.get_text(strip=True)
    location_date = ad.find('p', {'data-testid': 'location-date'})
    if location_date: 
        car_info['location_date'] = location_date.get_text(strip=True)
        if location_date and ' - ' in location_date:
            car_info['location'] = location_date.split(' - ')[0].strip()
    mileage_container = ad.find('div', class_='css-1kfqt7f')
    if mileage_container:
        mileage_span = mileage_container.find('span', class_='css-6as4g5')
        if mileage_span: car_info['mileage'] = mileage_span.get_text(strip=True)
    url_tag = ad.find('a', class_='css-1tqlkj0')
    if url_tag and url_tag.get('href'):
        car_info['reference_url'] = "https://www.olx.uz" + url_tag['href']
    return car_info

def filter_vehicle_ads(vehicle_ads):
    filtered = []
    for ad in vehicle_ads:
        price = ad.get('price', '').replace(' сум', '').replace(' ', '')
        mileage = ad.get('mileage', '')
        try:
            price = int(price)
        except ValueError:
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
    all_ads = [extract_car_ad_info(ad) for ad in ad_cards if extract_car_ad_info(ad)]
    filtered = filter_vehicle_ads(all_ads)
    log(f"Total ads found: {len(all_ads)}; After filtering: {len(filtered)}")
    return filtered

def parse_date(date_str):
    try:
        if "Сегодня" in date_str:
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return datetime.strptime(date_str, '%d %B %Y г.')
    except ValueError:
        logging.error(f"Failed to parse date: {date_str}")
        return None

def process_vehicle_data(vehicle_ads, brand, model):
    
    processed_ads = []
    for ad in vehicle_ads:
        try:
            uzs_price = ad.get('price', '').replace(' сум', '').replace(' ', '')
            usd_price = int(uzs_price) / UZSUM_TO_USD
        except ValueError:
            usd_price = None

        location_date = ad.get('location_date', '')
        location, date = location_date.split(' - ') if ' - ' in location_date else (location_date, None)

        mileage_info = ad.get('mileage', '').strip()
        year = mileage = None
        if ' - ' in mileage_info:
            year, mileage = mileage_info.split(' - ')
            year = int(year.strip()) if year.strip().isdigit() else None
            try:
                mileage = int(mileage.replace('км', '').replace(' ', '').strip())
            except ValueError:
                mileage = None
        elif mileage_info.strip().isdigit() and 2022 <= int(mileage_info.strip()) <= 2025:
            year = int(mileage_info.strip())
            mileage = 0

        created_at = parse_date(date.strip()) if date else None
        if created_at:
            created_at = tz_uzbekistan.localize(created_at)

        transmission = color = fuel_type = condition = extras = None
        # New fields for owner_type, body_type, owner_count
        owner_type = None
        body_type = None
        owner_count = None
        reference_url = ad.get('reference_url')
        if reference_url:
            try:
                detail_html = fetch_page(reference_url)
                params_div = detail_html.find('div', {'data-testid': 'ad-parameters-container'})
                if params_div:
                    params = params_div.find_all('p', class_='css-1los5bp')
                    # Inserted model check block
                    model_check_passed = True
                    expected_model = model.lower().split()[0]

                    for param in params:
                        text = param.get_text(strip=True)
                        if text.startswith('Модель:'):
                            detail_model = text.split(':', 1)[-1].strip().lower()
                            if expected_model not in detail_model:
                                log(f"⏩ Skipping ad due to model mismatch: expected '{model}', found '{detail_model}'")
                                model_check_passed = False
                                break
                    if not model_check_passed:
                        continue
                    for param in params:
                        text = param.get_text(strip=True)
                        if 'Коробка передач:' in text:
                            val = text.split(':')[-1].strip()
                            transmission = {
                                'Механическая': 'MT',
                                'Автоматическая': 'AT',
                                'Робот': 'DSG',
                                'Вариатор': 'CVT'
                            }.get(val)
                        elif 'Цвет:' in text:
                            val = text.split(':')[-1].strip()
                            color = {
                                'Белый': 'white',
                                'Черный': 'black',
                                'Серебристый': 'silver',
                                'Серый': 'grey',
                                'Синий': 'blue',
                                'Красный': 'red',
                                'Зеленый': 'green',
                                'Желтый': 'yellow',
                            }.get(val)
                        elif 'Вид топлива:' in text:
                            val = text.split(':')[-1].strip()
                            fuel_type = {
                                'Бензин': 'Gasoline',
                                'Дизель': 'Diesel',
                                'Электро': 'Electric',
                                'Газ': 'Gas',
                            }.get(val)
                        elif 'Состояние машины:' in text:
                            val = text.split(':')[-1].strip()
                            condition = {
                                'Отличное': 'ideal',
                                'Повреждено': 'damaged',
                                'Нуждается в ремонте': 'needs_repair',
                                'Б/у': 'used'
                            }.get(val)
                        elif 'Доп. опции:' in text:
                            extras = text.split(':', 1)[-1].strip()
                        # Inserted extraction for owner_type, body_type, owner_count
                        elif 'Частное лицо' in text or 'Компания' in text:
                            owner_type = text.strip()
                        elif 'Тип кузова:' in text:
                            body_type = text.split(':')[-1].strip()
                        elif 'Количество хозяев:' in text:
                            owner_count = text.split(':')[-1].strip()

                # Extract detailed description text
                desc_block = detail_html.find('div', class_='css-19duwlz')
                if desc_block:
                    ad["description_detail"] = desc_block.get_text(separator=' ', strip=True)

                # Extract owner name and profile info
                owner_name_tag = detail_html.find('h4', {'data-testid': 'user-profile-user-name'})
                ad["owner_name"] = owner_name_tag.get_text(strip=True) if owner_name_tag else None

                member_since_tag = detail_html.find('p', {'data-testid': 'member-since'})
                ad["owner_member_since"] = member_since_tag.get_text(strip=True) if member_since_tag else None

                last_seen_tag = detail_html.find('p', {'data-testid': 'lastSeenBox'})
                ad["owner_last_seen"] = last_seen_tag.get_text(strip=True) if last_seen_tag else None

                # Extract link to profile
                profile_link_tag = detail_html.find('a', {'data-testid': 'user-profile-link'})
                if profile_link_tag and profile_link_tag.get("href") and "/list/user/" in profile_link_tag["href"]:
                    ad["owner_profile_url"] = "https://www.olx.uz" + profile_link_tag["href"]
            except Exception as e:
                log(f"❌ Failed to fetch detail info from {reference_url}: {e}")

        if USE_SELENIUM and reference_url:
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        os.path.join(os.path.dirname(__file__), 'selenium_fetch_phone.py'),
                        reference_url,
                        'button[data-testid="show-phone"]'
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                log(f"stdout:\n{result.stdout.strip()}")
                if result.stderr:
                    log(f"stderr:\n{result.stderr.strip()}")
                if result.returncode == 0:
                    ad["owner_tel_number"] = result.stdout.strip()
                else:
                    log(f"❌ Selenium returned non-zero exit status {result.returncode}")
            except Exception as e:
                log(f"❌ Selenium fetch failed for phone number: {e}")

        # Add extra fields to ad dictionary
        ad["gear_type"] = transmission
        ad["color"] = color
        ad["fuel_type"] = fuel_type
        ad["condition"] = condition
        ad["additional_options"] = extras
        ad["owner_type"] = owner_type
        ad["body_type"] = body_type
        ad["owner_count"] = owner_count

        processed_ads.append({
            "brand": brand,
            "model": model,
            "year": year,
            "price": round(usd_price, 2) if usd_price else None,
            "description": ad.get('name'),
            "created_at": created_at,
            "mileage": mileage,
            "location": location.strip() if location else None,
            "reference_url": reference_url,
            "car_ad_id": reference_url.split('-')[-1].replace('.html', '') if reference_url else None,
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
            "owner_type": ad.get("owner_type"),
            "body_type": ad.get("body_type"),
            "owner_count": ad.get("owner_count"),
        })
    return processed_ads

def save_to_db(processed_ads):
    for ad in processed_ads:
        if ad.get("car_ad_id") and ad.get("description") and ad.get("created_at"):
            try:
                # Convert created_at to ISO format
                ad["created_at"] = ad["created_at"].isoformat()

                # Check if the ad with car_ad_id already exists
                params = {"car_ad_id": ad["car_ad_id"]}
                check_response = requests.get(API_URL_DB, params=params)
                if check_response.status_code == 200 and check_response.json():
                    log(f"Car already exists: {ad['car_ad_id']}")
                    continue

                # Try to POST full car ad
                post_response = requests.post(API_URL_DB, json=ad)
                if post_response.status_code == 201:
                    log(f"✅ Saved via API: {ad['car_ad_id']}")
                else:
                    log(f"❌ API error ({post_response.status_code}) for: {ad}")
            except Exception as e:
                logging.error(f"Request failed for car {ad}: {e}")
        else:
            logging.warning(f"Skipping invalid ad: {ad}")

def export_data_to_csv(brand="Chevrolet", model="Lacetti"):
    # Include color="white" in params and filter
    params = {"brand": brand, "model": model, "color": "white"}
    try:
        response = requests.get(API_URL_FILTERED, params=params)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            export_dir = '/app/databricks/data'
            if not os.path.exists(export_dir):
                export_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'databricks', 'data'))
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

    for pair in brand_model_pairs:
        brand = pair.get("brand")
        model = pair.get("model")
        if not brand or not model:
            log("⚠️ Skipping invalid brand-model pair.")
            continue

        search_phrase = f"{model} {brand}"
        ads = scrape_olx_for_vehicles(search_phrase)
        if TEST_MODE:
            raw_output_path = os.path.join(os.path.dirname(__file__), f'test_raw_output_{brand}_{model}.json')
            with open(raw_output_path, 'w', encoding='utf-8') as f:
                json.dump(ads, f, ensure_ascii=False, indent=2, default=str)
            log(f"✅ Test mode: saved raw ads to {raw_output_path}")

        processed = process_vehicle_data(ads, brand, model)

        if TEST_MODE:
            test_output_path = os.path.join(os.path.dirname(__file__), f'test_output_{brand}_{model}.json')
            with open(test_output_path, 'w', encoding='utf-8') as f:
                json.dump(processed, f, ensure_ascii=False, indent=2, default=str)
            log(f"✅ Test mode: saved data to {test_output_path}")
        else:
            save_to_db(processed)
            export_data_to_csv(brand="Chevrolet", model="Lacetti")

    log(f"Task completed at {datetime.now()}")

if __name__ == "__main__":
    main()