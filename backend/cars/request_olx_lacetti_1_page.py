import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Function to fetch and parse a page
def fetch_page(url):
    response = requests.get(url)
    logging.info(f"Fetched page: {url}")
    return BeautifulSoup(response.content, 'html.parser')

# Function to extract relevant information from a car ad
def extract_car_ad_info_old(ad):
    car_info = {}
    
    # Find the car name (title)
    title = ad.find('h4', class_='css-1s3qyje')
    if title:
        car_info['name'] = title.get_text(strip=True)
    
    # Find the price
    price = ad.find('p', class_='css-13afqrm')
    if price:
        car_info['price'] = price.get_text(strip=True)
    
    # Find the location and date
    location_date = ad.find('p', class_='css-1mwdrlh')
    if location_date:
        car_info['location_date'] = location_date.get_text(strip=True)
    
    # Find the mileage and year info (e.g., "2012 - 245 000 км")
    mileage_info = ad.find('span', class_='css-1cd0guq')
    if mileage_info:
        car_info['mileage'] = mileage_info.get_text(strip=True)

    # Extract the reference URL (ad's unique link)
    reference_url_tag = ad.find('a', class_='css-qo0cxu')  # Correct class for the reference URL
    if reference_url_tag and reference_url_tag.get('href'):
        car_info['reference_url'] = "https://www.olx.uz" + reference_url_tag['href']
    
    return car_info

# new version 5/05
def extract_car_ad_info(ad):
    car_info = {}

    # Title
    # old; css-1s3qyje
    title = ad.find('h4', class_='css-1g61gc2')
    if title:
        car_info['name'] = title.get_text(strip=True)

    # Price
    price = ad.find('p', {'data-testid': 'ad-price'})
    if price:
        car_info['price'] = price.get_text(strip=True)

    # Location and Date
    location_date = ad.find('p', {'data-testid': 'location-date'})
    if location_date:
        car_info['location_date'] = location_date.get_text(strip=True)

    # Mileage
    mileage_container = ad.find('div', class_='css-1kfqt7f')
    if mileage_container:
        mileage_span = mileage_container.find('span', class_='css-6as4g5')
        if mileage_span:
            car_info['mileage'] = mileage_span.get_text(strip=True)

    # Reference URL
    url_tag = ad.find('a', class_='css-1tqlkj0')
    if url_tag and url_tag.get('href'):
        car_info['reference_url'] = "https://www.olx.uz" + url_tag['href']

    return car_info

# Function to filter ads based on price and mileage
def filter_vehicle_ads(vehicle_ads):
    filtered_ads = []
    
    for ad in vehicle_ads:
        # Extract price and mileage
        price = ad.get('price', '').replace(' сум', '').replace(' ', '')
        mileage = ad.get('mileage', '')
        
        try:
            price = int(price)
        except ValueError:
            continue
        
        # Check if the price is between 70,000,000 and 200,000,000 and mileage is not empty
        if 70000000 <= price <= 200000000 and mileage:
            filtered_ads.append(ad)

    return filtered_ads

# Function to scrape and filter out vehicle ads from the first page
def scrape_olx_for_vehicles():
    base_url = 'https://www.olx.uz/list/q-lacceti/'  # Replace with the correct URL
    url = base_url  # Only scrape the first page

    logging.info(f"Scraping first page: {url}")
    soup = fetch_page(url)
    
    # Find all vehicle-related ads (filter out non-vehicle ads like tires)
    ad_cards = soup.find_all('div', {'data-cy': 'l-card'})
    
    all_vehicle_ads = []

    for ad in ad_cards:
        # Extract car ad info from each card
        car_info = extract_car_ad_info(ad)
        if car_info:
            all_vehicle_ads.append(car_info)
            logging.debug(f"Ad extracted: {car_info}")

    # Filter out ads based on the price and mileage
    filtered_ads = filter_vehicle_ads(all_vehicle_ads)
    logging.info(f"Total ads found: {len(all_vehicle_ads)}; After filtering: {len(filtered_ads)}")

    return filtered_ads
