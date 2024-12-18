# Run the scraper for the first page and display results
from request_olx_laseti_1_page import scrape_olx_for_vehicles

# Conversion rate
UZSUM_TO_USD = 13000

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
        mileage_info = ad.get('mileage', '')
        year, mileage = mileage_info.split(' - ') if ' - ' in mileage_info else (None, mileage_info)

        # Create new structured data
        processed_ad = {
            "Car Name": ad.get('name'),
            "Price (UZS)": ad.get('price'),
            "Price (USD)": f"${usd_price:.2f}" if usd_price else None,
            "Location": location.strip() if location else None,
            "Date": date.strip() if date else None,
            "Year": year.strip() if year else None,
            "Mileage (km)": mileage.strip() if mileage else None,
            "Reference URL": ad.get('reference_url'),
        }
        processed_ads.append(processed_ad)

    return processed_ads

# Scrape and process the ads
vehicle_ads = scrape_olx_for_vehicles()
processed_ads = process_vehicle_data(vehicle_ads)

# Print the structured data for the filtered ads
for ad in processed_ads:
    print(f"Car Name: {ad['Car Name']}")
    print(f"Price (UZS): {ad['Price (UZS)']}")
    print(f"Price (USD): {ad['Price (USD)']}")
    print(f"Location: {ad['Location']}")
    print(f"Date: {ad['Date']}")
    print(f"Year: {ad['Year']}")
    print(f"Mileage (km): {ad['Mileage (km)']}")
    print(f"Reference URL: {ad['Reference URL']}")
    print("-" * 40)

# Summary
total_ads = len(processed_ads)
print(f"Total Ads: {total_ads}")