from django.urls import path
from .views import CarList, CarDetail, FuelTypeSummary, CarFiltersSummary, CarFilteredList

urlpatterns = [
    path('cars/', CarList.as_view(), name='car-list'),          # List all cars or create a new car
    path('cars/<int:pk>/', CarDetail.as_view(), name='car-detail'),  # Retrieve, update, or delete a car
    path('cars/fuel-type-summary/', FuelTypeSummary.as_view()),  # Summery of cars' fuel type and count
    path('cars/filters-summary/', CarFiltersSummary.as_view(), name='filters-summary'),
    path('cars/filtered-list/', CarFilteredList.as_view(), name='filtered-car-list'),
]