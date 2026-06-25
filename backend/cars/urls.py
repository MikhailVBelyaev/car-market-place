from django.urls import path
from .views import (CarList, CarDetail, FuelTypeSummary, CarFiltersSummary, CarFilteredList,
                    DropdownOptions, BrandModels, PriceHistory, SmartPrice,
                    BrandRanking, PriceMovers, WeeklyDigest,
                    PostConfig, ColorPremium, GearPremium, AgeDepreciation,
                    BestValue, SeasonalTrends, MarketBreadth, MileageDepreciation,
                    ApartmentList, ElectronicsList)

urlpatterns = [
    path('cars/', CarList.as_view(), name='car-list'),
    path('apartments/', ApartmentList.as_view(), name='apartment-list'),
    path('electronics/', ElectronicsList.as_view(), name='electronics-list'),
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
    # Post config
    path('cars/post-config/',                 PostConfig.as_view(), name='post-config'),
    path('cars/post-config/<str:post_type>/', PostConfig.as_view(), name='post-config-detail'),
    # Analytics — new endpoints
    path('cars/analytics/color-premium/',        ColorPremium.as_view(),        name='color-premium'),
    path('cars/analytics/gear-premium/',         GearPremium.as_view(),         name='gear-premium'),
    path('cars/analytics/age-depreciation/',     AgeDepreciation.as_view(),     name='age-depreciation'),
    path('cars/analytics/best-value/',           BestValue.as_view(),           name='best-value'),
    path('cars/analytics/seasonal-trends/',      SeasonalTrends.as_view(),      name='seasonal-trends'),
    path('cars/analytics/market-breadth/',       MarketBreadth.as_view(),       name='market-breadth'),
    path('cars/analytics/mileage-depreciation/', MileageDepreciation.as_view(), name='mileage-depreciation'),
    # Shortcuts for existing analytics (for admin preview)
    path('cars/analytics/brand-ranking/',  BrandRanking.as_view()),
    path('cars/analytics/price-movers/',   PriceMovers.as_view()),
    path('cars/analytics/weekly-digest/',  WeeklyDigest.as_view()),
]
