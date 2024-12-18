import os
import sys

# Add the 'cars' directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'cars'))

# Set up Django environment
# Correct path to the settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "car_marketplace.settings")

import django
from datetime import datetime

# Set up Django before importing models
django.setup()

# Now, you can safely import the models and other Django-dependent components
from cars.request_olx_lacetti_1_page import scrape_olx_for_vehicles
from cars.Scrape_olx_lacceti import process_vehicle_data, save_to_db
from cars.models import Car

def main():
    print(f"Task started at {datetime.now()}")

    # Step 1: Scrape data
    print("Scraping data from OLX...")
    vehicle_ads = scrape_olx_for_vehicles()
    print(f"Scraped {len(vehicle_ads)} ads.")

    # Step 2: Process data
    print("Processing scraped data...")
    processed_data = process_vehicle_data(vehicle_ads)
    print(f"Processed {len(processed_data)} ads.")

    # Step 3: Save to database
    print("Saving data to database...")
    save_to_db(processed_data)
    print("Data saved successfully.")

    print(f"Task completed at {datetime.now()}")

if __name__ == "__main__":
    main()