from django.urls import path
from .views import (CarList, CarDetail, FuelTypeSummary, CarFiltersSummary, CarFilteredList,
                    DropdownOptions, BrandModels, PriceHistory, SmartPrice,
                    BrandRanking, PriceMovers, WeeklyDigest)

urlpatterns = [
    path('cars/', CarList.as_view(), name='car-list'),
    path('cars/<int:pk>/', CarDetail.as_view(), name='car-detail'),
    path('cars/fuel-type-summary/', FuelTypeSummary.as_view()),
    path('cars/filters-summary/', CarFiltersSummary.as_view(), name='filters-summary'),
    path('cars/filtered-list/', CarFilteredList.as_view(), name='filtered-car-list'),
    path('cars/dropdown-options/', DropdownOptions.as_view()),
    path('cars/brand-models/',    BrandModels.as_view(),   name='brand-models'),
    path('cars/price-history/',   PriceHistory.as_view(),  name='price-history'),
    path('cars/smart-price/',     SmartPrice.as_view(),    name='smart-price'),
    path('cars/brand-ranking/',   BrandRanking.as_view(),  name='brand-ranking'),
    path('cars/price-movers/',    PriceMovers.as_view(),   name='price-movers'),
    path('cars/weekly-digest/',   WeeklyDigest.as_view(),  name='weekly-digest'),
]