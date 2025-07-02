import pytest
from rest_framework.test import APIClient
from django.utils.timezone import make_aware
from datetime import datetime
from cars.models import Car

@pytest.mark.django_db
def setup_test_data():
    created_date = make_aware(datetime(2025, 7, 2))
    for i in range(10):
        Car.objects.create(
            car_ad_id=f"ad-{i}",
            description="Test Car",
            price=15000,
            mileage=40000,
            fuel_type="Electric",
            gear_type="AT",
            color="white",
            brand="Tesla",
            model="Model Y",
            year=2021,
            created_at=created_date
        )

@pytest.mark.django_db
def test_all_requests():
    setup_test_data()
    client = APIClient()
    base = "/api/cars/filtered-list/"
    queries = [
        "?created_at=2025-06-29-2025-07-02",
        "?created_at=2025-07-02",
        "?created_at=2025-06-25-2025-07-02",
        "?created_at=2025-06-02-2025-07-02",
        "",
        "?fuel_type=Electric&created_at=2025-06-29-2025-07-02",
        "?fuel_type=Electric&gear_type=AT&created_at=2025-06-29-2025-07-02",
        "?fuel_type=Electric&gear_type=AT&color=white&created_at=2025-06-29-2025-07-02",
        "?fuel_type=Electric&gear_type=AT&color=white&brand=BYD&created_at=2025-06-29-2025-07-02",
        "?fuel_type=Electric&gear_type=AT&color=white&brand=Zikr&created_at=2025-06-29-2025-07-02",
        "?fuel_type=Electric&gear_type=AT&color=white&brand=Tesla&created_at=2025-06-29-2025-07-02",
        "?fuel_type=Electric&gear_type=AT&color=white&brand=Tesla&model=Model+Y&created_at=2025-06-29-2025-07-02",
        "?fuel_type=Electric&gear_type=AT&color=white&brand=Tesla&model=Model+Y&year=2021&created_at=2025-06-29-2025-07-02",
        "?fuel_type=Electric&gear_type=AT&color=white&brand=Tesla&model=Model+Y&year=2021&price=10000-20000&created_at=2025-06-29-2025-07-02",
        "?fuel_type=Electric&gear_type=AT&color=white&brand=Tesla&model=Model+Y&year=2021&price=10000-20000&mileage=0-50000&created_at=2025-06-29-2025-07-02"
    ]

    for query in queries:
        response = client.get(base + query)
        assert response.status_code == 200
        assert "results" in response.json()
        assert isinstance(response.json()["results"], list)