import json

with open("dump_cars.json", "r") as f:
    data = json.load(f)

total = len(data)
missing_ids = sum(1 for ad in data if not ad.get("fields", {}).get("car_ad_id"))
unique_ids = len(set(ad["fields"]["car_ad_id"] for ad in data if ad.get("fields", {}).get("car_ad_id")))

print(f"📦 Total ads in dump: {total}")
print(f"⚠️ Missing car_ad_id: {missing_ids}")
print(f"✅ Unique car_ad_id: {unique_ids}")

with open("dump_cars.json") as f:
    print(json.load(f)[2000])