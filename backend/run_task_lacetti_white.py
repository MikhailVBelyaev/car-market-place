import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
from cars.Scrape_olx_lacceti import process_vehicle_data, save_to_db, export_data_to_csv
from cars.models import Car

def main():
    logging.info(f"Task started at {datetime.now()}")

    # Step 1: Scrape data
    logging.info("Scraping data from OLX...")
    vehicle_ads = scrape_olx_for_vehicles()
    logging.info(f"Scraped {len(vehicle_ads)} ads.")

    # Step 2: Process data
    logging.info("Processing scraped data...")
    processed_data = process_vehicle_data(vehicle_ads)
    logging.info(f"Processed {len(processed_data)} ads.")

    # Step 3: Save to database
    logging.info("Saving data to database...")
    save_to_db(processed_data)
    logging.info("Data saved successfully.")

    # Step 4: Export to CSV
    logging.info("Exporting latest car data to CSV...")
    export_data_to_csv(brand="Chevrolet", model="Lacetti")
    logging.info("CSV export complete.")

    logging.info(f"Task completed at {datetime.now()}")

if __name__ == "__main__":
    main()