import requests
from bs4 import BeautifulSoup

# Function to fetch and parse a page
def fetch_page(url):
    response = requests.get(url)
    return BeautifulSoup(response.content, 'html.parser')

# Function to extract relevant information from a car ad
def extract_car_ad_info(ad):
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
    
    return car_info

# Function to scrape and filter out vehicle ads
def scrape_olx_for_vehicles():
    base_url = 'https://www.olx.uz/list/q-laseti/'  # Replace with the correct URL
    pages_to_scrape = 5  # Scrape first 5 pages

    all_vehicle_ads = []

    for page in range(1, pages_to_scrape + 1):
        url = f'{base_url}?page={page}'
        print(f"Scraping page {page}...")
        soup = fetch_page(url)
        
        # Find all vehicle-related ads (filter out non-vehicle ads like tires)
        ad_cards = soup.find_all('div', {'data-cy': 'l-card'})
        
        for ad in ad_cards:
            # Extract car ad info from each card
            car_info = extract_car_ad_info(ad)
            if car_info:
                all_vehicle_ads.append(car_info)

    # Return a structured table of data
    return all_vehicle_ads

# Run the scraper and display results
vehicle_ads = scrape_olx_for_vehicles()

# Print the structured data
for ad in vehicle_ads:
    print(f"Car Name: {ad.get('name')}")
    print(f"Price: {ad.get('price')}")
    print(f"Location and Date: {ad.get('location_date')}")
    print(f"Mileage: {ad.get('mileage')}")
    print("-" * 40)