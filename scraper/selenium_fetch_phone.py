import sys
import time
import logging
# Configure logging and printing
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("selenium_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

if len(sys.argv) < 3:
    print("Usage: python selenium_fetch_phone.py <url> <button_selector>")
    sys.exit(1)

url = sys.argv[1]
button_selector = sys.argv[2]

logging.info(f"Received URL: {url}")
logging.info(f"Button selector: {button_selector}")

# Configure Selenium options
chrome_options = Options()
# chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-background-timer-throttling")
# Optionally set window size for better visibility
chrome_options.add_argument("--window-size=1200,800")

driver = webdriver.Chrome(options=chrome_options)

try:
    try:
        driver.get(url)
        logging.info(f"Opened URL: {url}")
    except Exception as e:
        logging.exception("Failed to open URL")
        sys.exit(1)

    # Try to close cookie overlay if it exists
    try:
        try:
            cookie_banner = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="cookies-overlay__container"] button'))
            )
            cookie_banner.click()
            logging.info("Closed cookie overlay.")
        except Exception:
            logging.info("No cookie overlay found.")
    except Exception:
        logging.info("Failed during cookie overlay handling.")

    try:
        logging.info(f"Waiting for button with selector: {button_selector}")
        show_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
        )
        show_button.click()
        logging.info("Clicked 'show phone' button.")
    except Exception as e:
        logging.exception("Failed to find or click the 'show phone' button")
        sys.exit(1)

    try:
        logging.info("Waiting for phone link to appear...")
        phone_elem = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-testid="contact-phone"]'))
        )
        href = phone_elem.get_attribute("href")
        if href and href.startswith("tel:"):
            phone_number = href.replace("tel:", "").strip()
            logging.info(f"Extracted phone number: {phone_number}")
            print(phone_number)
        else:
            raise Exception("Phone element found but 'tel:' not present in href")
    except Exception as e:
        logging.exception("Failed to extract phone number")
        sys.exit(1)

except Exception as e:
    logging.exception("Selenium error occurred:")
    logging.error(f"Selenium error: {str(e)}")
    sys.exit(1)
finally:
    logging.info("Closing browser")
    driver.quit()