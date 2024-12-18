from datetime import datetime
from request_olx_lacetti_1_page import scrape_olx_for_vehicles
from cars.models import Car  
import logging
import locale
from pytz import timezone

# Set locale for month name parsing (Russian in this case)
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

# Define the timezone for Uzbekistan
tz_uzbekistan = timezone('Asia/Tashkent')

# Conversion rate
UZSUM_TO_USD = 13000

def parse_date(date_str):
    """
    Parses the date in Russian format and converts it to a datetime object.
    Handles "Сегодня" for today's date and normal date strings.
    Example: 
    - '23 ноября 2024 г.' -> datetime(2024, 11, 23)
    - 'Сегодня в 04:32' -> datetime(2024, 12, 18)
    """
    try:
        # Handle "Сегодня" (Today)
        if "Сегодня" in date_str:
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Parse the date string (Russian month names)
            return datetime.strptime(date_str, '%d %B %Y г.')
    except ValueError:
        logging.error(f"Failed to parse date: {date_str}")
        return None  # Return None if parsing fails

def process_vehicle_data(vehicle_ads):
    processed_ads = []
    for ad in vehicle_ads:
        # Convert price to USD
        uzs_price = ad.get('price', '').replace(' сум', '').replace(' ', '')
        try:
            usd_price = int(uzs_price) / UZSUM_TO_USD
        except ValueError:
            usd_price = None

        # Separate location and date
        location_date = ad.get('location_date', '')
        location, date = location_date.split(' - ') if ' - ' in location_date else (location_date, None)

        # Split year and mileage
        mileage_info = ad.get('mileage', '').strip()
        #print(f"mileage_info: {mileage_info}")
        year = None
        mileage = None  # Default to None for mileage

        if ' - ' in mileage_info:
            year, mileage = mileage_info.split(' - ')
            year = int(year.strip()) if year.strip().isdigit() else None
            try:
            # Format mileage as an integer
                mileage = int(mileage.replace('км', '').replace(' ', '').strip())
            except ValueError:
                mileage = None  # In case of an invalid mileage format
        else:
            # Handle case where only the year is present
            mileage_info_cleaned = mileage_info.strip()
            if mileage_info_cleaned.isdigit() and 2022 <= int(mileage_info_cleaned) <= 2025:
                year = int(mileage_info_cleaned)
                mileage = 0  # Set mileage to 0 for new vehicles with no mileage information

        # Parse date to datetime format using the parse_date function and make it timezone-aware
        created_at = parse_date(date.strip()) if date else None
        if created_at:
            created_at = tz_uzbekistan.localize(created_at)

        # Create new structured data
        processed_ad = {
            "brand": "Chevrolet",
            "model": "Lacetti",
            "year": year,
            "price": round(usd_price, 2) if usd_price else None,
            "description": ad.get('name'),
            "created_at": created_at,
            "mileage": mileage,
        }
        processed_ads.append(processed_ad)

    return processed_ads

def save_to_db(processed_ads):
    for ad in processed_ads:
        # Ensure essential fields are not None or empty
        if ad.get("year") and ad.get("description") and ad.get("created_at"):
            # Check for uniqueness before saving
            if not Car.objects.filter(
                year=ad["year"],
                description=ad["description"],
                created_at=ad["created_at"]
            ).exists():
                try:
                    # Create and save the Car object if not exists
                    Car.objects.create(
                        brand=ad["brand"],
                        model=ad["model"],
                        year=ad["year"],
                        price=ad["price"],
                        description=ad["description"],
                        created_at=ad["created_at"],
                        mileage=ad["mileage"],
                    )
                    print(f"Saved car: {ad['brand']} {ad['model']} {ad['year']}")  # Log successful save
                except Exception as e:
                    logging.error(f"Error saving car {ad['brand']} {ad['model']}: {e}")
            else:
                print(f"Car already exists: {ad['brand']} {ad['model']} {ad['year']}")  # Log duplicates
        else:
            print(f"Skipping invalid ad: {ad}")  # Log invalid ads