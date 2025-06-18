# This script is designed to predict the price of a Chevrolet Lacetti car based on user input for year and mileage.
# It uses a machine learning model hosted on Databricks and requires the user to input valid year and mileage values.
# The script handles input validation and API requests, providing feedback to the user
import requests
from dotenv import load_dotenv
import os

# Fixed car info
BRAND = "Chevrolet"
MODEL = "Lacetti"

# Databricks API config (replace with your actual values)
load_dotenv()

DATABRICKS_URL = os.getenv("DATABRICKS_URL")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

def get_user_input():
    while True:
        try:
            year = int(input("Enter car year: "))
            if not (2000 <= year <= 2025):
                print("❌ Year must be between 2000 and 2025.")
                continue
            break
        except ValueError:
            print("❌ Please enter a valid integer for year.")
    
    while True:
        try:
            miles = int(input("Enter car mileage: "))
            if not (0 <= miles <= 500000):
                print("❌ Mileage must be between 0 and 500000.")
                continue
            break
        except ValueError:
            print("❌ Please enter a valid integer for mileage.")
    
    return year, miles

def predict_price(year, miles):
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
    "inputs": [
        {
            "year": year,
            "mileage": miles
        }
        ]
    }
    response = requests.post(DATABRICKS_URL, json=payload, headers=headers)
    if response.status_code == 200:
        output = response.json()
        price = output["predictions"][0]
        rounded_price = round(price, -2)
        print(f"Predicted price for your car: {int(rounded_price)} USD")
    else:
        if "not ready" in response.text.lower():
            print("The model is still loading. Please wait and try again in 1–2 minutes.")
        else:
            print("❌ Failed to get prediction:", response.text)

def main():
    print ("In MVP version, we only support Chevrolet Lacetti white.")
    year, miles = get_user_input()
    predict_price(year, miles)

if __name__ == "__main__":
    main()