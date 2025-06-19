# scraper/olx_scraper.py
import requests
from bs4 import BeautifulSoup
import logging

def fetch_page(url):
    response = requests.get(url)
    logging.info(f"Fetched page: {url}")
    return BeautifulSoup(response.content, 'html.parser')

def extract_ads(soup):
    ad_cards = soup.find_all('div', {'data-cy': 'l-card'})
    ads = []
    for ad in ad_cards:
        car_info = {}
        title = ad.find('h4', class_='css-1g61gc2')
        price = ad.find('p', {'data-testid': 'ad-price'})
        loc_date = ad.find('p', {'data-testid': 'location-date'})
        mileage_div = ad.find('div', class_='css-1kfqt7f')
        if mileage_div:
            mileage = mileage_div.find('span', class_='css-6as4g5')
        else:
            mileage = None
        link = ad.find('a', class_='css-1tqlkj0')

        if title: car_info['name'] = title.get_text(strip=True)
        if price: car_info['price'] = price.get_text(strip=True)
        if loc_date: car_info['location_date'] = loc_date.get_text(strip=True)
        if mileage: car_info['mileage'] = mileage.get_text(strip=True)
        if link and link.get('href'):
            car_info['reference_url'] = "https://www.olx.uz" + link['href']

        ads.append(car_info)
    return ads

def scrape_olx():
    url = 'https://www.olx.uz/list/q-lacceti/'
    logging.info(f"Scraping OLX: {url}")
    soup = fetch_page(url)
    ads = extract_ads(soup)
    logging.info(f"Found {len(ads)} ads.")
    return ads
