import requests
from dotenv import load_dotenv
import os

# Fixed car info
BRAND = "Chevrolet"
MODEL = "Lacetti"
GEAR = "AT"

# Databricks API config (replace with your actual values)
load_dotenv()

DATABRICKS_URL = os.getenv("DATABRICKS_URL")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

def get_user_input():
    year = int(input("Enter car year: "))
    miles = int(input("Enter car mileage: "))
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
        print("Failed to get prediction:", response.text)

def main():
    print ("In MVP version, we only support Chevrolet Lacetti")
    year, miles = get_user_input()
    predict_price(year, miles)

if __name__ == "__main__":
    main()