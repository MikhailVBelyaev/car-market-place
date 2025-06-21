import os
import sys
import logging
import locale
from datetime import datetime
from pytz import timezone
import pandas as pd
import requests
from bs4 import BeautifulSoup

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
API_URL = 'http://localhost:8000/api/cars/'  # Update with your actual API endpoint
API_URL = 'http://django:8000/api/cars/' 

# Set up Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), 'cars'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "car_marketplace.settings")
import django
django.setup()

from cars.models import Car

# Locale and timezone config
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
tz_uzbekistan = timezone('Asia/Tashkent')
UZSUM_TO_USD = 13000

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
    if location_date: car_info['location_date'] = location_date.get_text(strip=True)
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
        if 70000000 <= price <= 200000000 and mileage:
            filtered.append(ad)
    return filtered

def scrape_olx_for_vehicles():
    url = 'https://www.olx.uz/list/q-lacceti/'
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

def process_vehicle_data(vehicle_ads):
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

        processed_ads.append({
            "brand": "Chevrolet",
            "model": "Lacetti",
            "year": year,
            "price": round(usd_price, 2) if usd_price else None,
            "description": ad.get('name'),
            "created_at": created_at,
            "mileage": mileage,
        })
    return processed_ads

def save_to_db(processed_ads):
    for ad in processed_ads:
        if ad.get("year") and ad.get("description") and ad.get("created_at"):
            try:
                # Convert created_at to ISO format
                ad["created_at"] = ad["created_at"].isoformat()

                # Check if a similar car already exists via API
                params = {
                    "year": ad["year"],
                    "description": ad["description"],
                    "created_at": ad["created_at"]
                }
                check_response = requests.get(API_URL, params=params)
                if check_response.status_code == 200 and check_response.json():
                    log(f"Car already exists: {ad['brand']} {ad['model']} {ad['year']}")
                    continue

                # Try to POST new ad
                post_response = requests.post(API_URL, json=ad)
                if post_response.status_code == 201:
                    log(f"✅ Saved via API: {ad['brand']} {ad['model']} {ad['year']}")
                else:
                    log(f"❌ API error ({post_response.status_code}) for: {ad}")
            except Exception as e:
                logging.error(f"Request failed for car {ad}: {e}")
        else:
            logging.warning(f"Skipping invalid ad: {ad}")

def save_to_db_intern_old(processed_ads):
    for ad in processed_ads:
        if ad.get("year") and ad.get("description") and ad.get("created_at"):
            if not Car.objects.filter(
                year=ad["year"],
                description=ad["description"],
                created_at=ad["created_at"]
            ).exists():
                try:
                    Car.objects.create(**ad)
                    log(f"Saved car: {ad['brand']} {ad['model']} {ad['year']}")
                except Exception as e:
                    logging.error(f"Error saving car {ad['brand']} {ad['model']}: {e}")
            else:
                log(f"Car already exists: {ad['brand']} {ad['model']} {ad['year']}")
        else:
            logging.warning(f"Skipping invalid ad: {ad}")

def export_data_to_csv_old_use_car_object(brand="Chevrolet", model="Lacetti"):
    queryset = Car.objects.filter(
        brand=brand, model=model,
        mileage__isnull=False, price__isnull=False, created_at__isnull=False
    ).values("year", "mileage", "price", "created_at")

    df = pd.DataFrame.from_records(queryset)
    export_dir = '/app/databricks/data'
    # test path for local development
    if not os.path.exists(export_dir):
        export_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'databricks', 'data'))
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, 'cars_latest.csv')
    df.to_csv(export_path, index=False)
    log(f"✅ CSV exported to: {export_path} (rows: {len(df)})")

def export_data_to_csv(brand="Chevrolet", model="Lacetti"):
    params = {"brand": brand, "model": model}
    try:
        response = requests.get(API_URL, params=params)
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
    ads = scrape_olx_for_vehicles()
    processed = process_vehicle_data(ads)
    save_to_db(processed)
    export_data_to_csv()
    log(f"Task completed at {datetime.now()}")

if __name__ == "__main__":
    main()