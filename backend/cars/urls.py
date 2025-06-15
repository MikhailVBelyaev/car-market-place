from django.urls import path
from .views import CarList, CarDetail

urlpatterns = [
    path('cars/', CarList.as_view(), name='car-list'),          # List all cars or create a new car
    path('cars/<int:pk>/', CarDetail.as_view(), name='car-detail'),  # Retrieve, update, or delete a car
]