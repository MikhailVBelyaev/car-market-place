from django.db.models import Avg, Count, Min, Max, Q
from django.db import connection
from rest_framework import serializers
from django.db.models.functions import TruncDate, TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Car, Apartment, Electronics
from .serializers import CarSerializer, ApartmentSerializer, ElectronicsSerializer
import logging
import urllib.request
import json as _json
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils import timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Live USD/UZS rate from Central Bank of Uzbekistan, cached 24 h
# ---------------------------------------------------------------------------
_uzs_rate_cache: dict = {'rate': 12800, 'fetched_at': None}

def _get_uzs_rate() -> float:
    cache = _uzs_rate_cache
    now = datetime.now(dt_timezone.utc)
    if cache['fetched_at'] and (now - cache['fetched_at']).total_seconds() < 86400:
        return cache['rate']
    try:
        with urllib.request.urlopen(
            'https://cbu.uz/en/arkhiv-kursov-valyut/json/USD/', timeout=4
        ) as resp:
            data = _json.loads(resp.read())
            rate = float(data[0]['Rate'])
            cache['rate'] = rate
            cache['fetched_at'] = now
            logger.info(f'UZS rate refreshed: 1 USD = {rate} UZS')
            return rate
    except Exception as e:
        logger.warning(f'UZS rate fetch failed ({e}), using cached {cache["rate"]}')
        return cache['rate']

class CarShortSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = ['description', 'price', 'location', 'created_at', 'year', 'mileage', 'reference_url']

    def get_created_at(self, obj):
        if obj.created_at:
            return obj.created_at.date()
        return None

class CarList(APIView):
    def get(self, request):
        car_ad_id = request.query_params.get("car_ad_id")
        if car_ad_id:
            cars = Car.objects.filter(car_ad_id=car_ad_id)
        else:
            cars = Car.objects.all()
        serializer = CarSerializer(cars, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Upsert: if a car with this car_ad_id already exists, return 200
        # "exists" instead of attempting an insert that would fail the unique
        # constraint. The scraper v2 treats both 200 and 201 as success.
        ad_id = request.data.get('car_ad_id')
        if ad_id and Car.objects.filter(car_ad_id=ad_id).exists():
            return Response({'status': 'exists', 'car_ad_id': ad_id}, status=status.HTTP_200_OK)
        serializer = CarSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ApartmentList(APIView):
    """List real estate listings, or upsert one (POST from the scraper).

    Mirrors CarList: a POST with an ad_id that already exists returns 200
    'exists' rather than failing the PK constraint, so the scraper can treat
    both 200 and 201 as success (ON CONFLICT DO NOTHING semantics).
    """
    def get(self, request):
        ad_id = request.query_params.get("ad_id")
        property_type = request.query_params.get("property_type")
        qs = Apartment.objects.all()
        if ad_id:
            qs = qs.filter(ad_id=ad_id)
        if property_type:
            qs = qs.filter(property_type=property_type)
        serializer = ApartmentSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        ad_id = request.data.get('ad_id')
        if ad_id and Apartment.objects.filter(ad_id=ad_id).exists():
            return Response({'status': 'exists', 'ad_id': ad_id}, status=status.HTTP_200_OK)
        serializer = ApartmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ElectronicsList(APIView):
    """List electronics listings, or upsert one (POST from the scraper)."""
    def get(self, request):
        ad_id = request.query_params.get("ad_id")
        category = request.query_params.get("category")
        qs = Electronics.objects.all()
        if ad_id:
            qs = qs.filter(ad_id=ad_id)
        if category:
            qs = qs.filter(category=category)
        serializer = ElectronicsSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        ad_id = request.data.get('ad_id')
        if ad_id and Electronics.objects.filter(ad_id=ad_id).exists():
            Electronics.objects.filter(ad_id=ad_id).update(scraped_at=timezone.now())
            return Response({'status': 'exists', 'ad_id': ad_id}, status=status.HTTP_200_OK)
        serializer = ElectronicsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FuelTypeSummary(APIView):
    def get(self, request):
        summary = (
            Car.objects.values('fuel_type')
            .annotate(count=Count('pk'))
        )
        result = {
            entry['fuel_type'] if entry['fuel_type'] is not None else 'None': entry['count']
            for entry in summary
        }
        return Response(result)

class CarDetail(APIView):
    def get(self, request, pk):
        try:
            car = Car.objects.get(pk=pk)
            serializer = CarSerializer(car)
            return Response(serializer.data)
        except Car.DoesNotExist:
            return Response({"error": "Car not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        try:
            car = Car.objects.get(pk=pk)
            serializer = CarSerializer(car, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Car.DoesNotExist:
            return Response({"error": "Car not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            car = Car.objects.get(pk=pk)
            car.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Car.DoesNotExist:
            return Response({"error": "Car not found"}, status=status.HTTP_404_NOT_FOUND)

class CarFiltersSummary(APIView):
    def get(self, request):
        fields = ['fuel_type', 'gear_type', 'color', 'vehicle_type', 'condition', 'brand', 'model', 'year', 'created_at']
        result = {}
        for field in fields:
            if field == 'created_at':
                summary = (
                    Car.objects.annotate(date=TruncDate('created_at'))
                    .values('date')
                    .annotate(count=Count('*'))
                    .order_by('-date')
                )
                result[field] = {
                    str(entry['date']) if entry['date'] is not None else 'None': entry['count']
                    for entry in summary
                }
            else:
                summary = (
                    Car.objects.values(field)
                    .annotate(count=Count('*'))
                    .order_by('-count')
                )
                result[field] = {
                    str(entry[field]) if entry[field] is not None else 'None': entry['count']
                    for entry in summary
                }
            logger.debug(f"Summary for {field}: {result[field]}")
        return Response(result)

def build_filter_config(queryset, allowed):
    """
    Build filter configuration with counts based on the provided queryset.
    """
    filter_config = {}
    today = timezone.now().date()
    last_3_days = today - timedelta(days=3)
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)

    for key in allowed:
        if key == "fuel_type":
            values = queryset.values('fuel_type').annotate(count=Count('pk'))
            values_dict = {entry['fuel_type'] if entry['fuel_type'] is not None else 'None': entry['count'] for entry in values}
            opts = [
                {"value": "Gasoline", "label": "Gasoline", "count": values_dict.get("Gasoline", 0)},
                {"value": "Electric", "label": "Electric", "count": values_dict.get("Electric", 0)},
                {"value": "Diesel", "label": "Diesel", "count": values_dict.get("Diesel", 0)},
                {"value": "Hybrid", "label": "Hybrid", "count": values_dict.get("Hybrid", 0)},
                {"value": "Gas", "label": "Gas", "count": values_dict.get("Gas", 0)},
                {"value": "None", "label": "None", "count": values_dict.get("None", 0)}
            ]
            filter_config[key] = {"type": "checkbox", "options": opts}
        elif key == "gear_type":
            values = queryset.values('gear_type').annotate(count=Count('pk'))
            values_dict = {entry['gear_type'] if entry['gear_type'] is not None else 'None': entry['count'] for entry in values}
            opts = [
                {"value": "AT", "label": "Automatic", "count": values_dict.get("AT", 0)},
                {"value": "MT", "label": "Manual", "count": values_dict.get("MT", 0)},
                {"value": "DSG", "label": "Dual-clutch", "count": values_dict.get("DSG", 0)},
                {"value": "None", "label": "None", "count": values_dict.get("None", 0)}
            ]
            filter_config[key] = {"type": "checkbox", "options": opts}
        elif key == "year":
            values = queryset.values('year').annotate(count=Count('pk'))
            values_dict = {str(entry['year']) if entry['year'] is not None else 'None': entry['count'] for entry in values}
            years = []
            invalid_years = []
            for v in values_dict.keys():
                try:
                    y = int(v)
                    if 1900 <= y <= 2025:
                        years.append(y)
                    else:
                        invalid_years.append(v)
                except (ValueError, TypeError):
                    invalid_years.append(v)
                    continue
            if invalid_years:
                logger.warning(f"Invalid year values found: {invalid_years}")
            years = sorted(years, reverse=True)
            logger.debug(f"Processed years: {years}")
            opts = []
            for y in range(2020, 2026):
                opts.append({
                    "value": str(y),
                    "label": str(y),
                    "count": values_dict.get(str(y), 0)
                })
            group_2015_2019 = sum([values_dict.get(str(y), 0) for y in range(2015, 2020)])
            opts.append({
                "value": "2015-2019",
                "label": "2015–2019",
                "count": group_2015_2019
            })
            group_2010_2014 = sum([values_dict.get(str(y), 0) for y in range(2010, 2015)])
            opts.append({
                "value": "2010-2014",
                "label": "2010–2014",
                "count": group_2010_2014
            })
            group_2000_2009 = sum([values_dict.get(str(y), 0) for y in range(2000, 2010)])
            opts.append({
                "value": "2000-2009",
                "label": "2000–2009",
                "count": group_2000_2009
            })
            group_1990_1999 = sum([values_dict.get(str(y), 0) for y in range(1990, 2000)])
            opts.append({
                "value": "1990-1999",
                "label": "1990–1999",
                "count": group_1990_1999
            })
            group_1980_1989 = sum([values_dict.get(str(y), 0) for y in range(1980, 1990)])
            opts.append({
                "value": "1980-1989",
                "label": "1980–1989",
                "count": group_1980_1989
            })
            group_before_1980 = sum([values_dict.get(str(y), 0) for y in range(1900, 1980)])
            opts.append({
                "value": "before-1980",
                "label": "Before 1980",
                "count": group_before_1980
            })
            filter_config[key] = {"type": "dropdown", "options": opts}
        elif key == "price":
            opts = [
                {"value": "0-5000", "label": "Under $5,000", "count": queryset.filter(price__lte=5000).count()},
                {"value": "5000-10000", "label": "$5,000 - $10,000", "count": queryset.filter(price__range=(5000, 10000)).count()},
                {"value": "10000-20000", "label": "$10,000 - $20,000", "count": queryset.filter(price__range=(10000, 20000)).count()},
                {"value": "20000-50000", "label": "$20,000 - $50,000", "count": queryset.filter(price__range=(20000, 50000)).count()},
                {"value": "50000-", "label": "Over $50,000", "count": queryset.filter(price__gt=50000).count()}
            ]
            filter_config[key] = {"type": "checkbox", "options": opts}
        elif key == "mileage":
            opts = [
                {"value": "0-50000", "label": "Under 50,000 km", "count": queryset.filter(mileage__lte=50000).count()},
                {"value": "50000-100000", "label": "50,000 - 100,000 km", "count": queryset.filter(mileage__range=(50000, 100000)).count()},
                {"value": "100000-150000", "label": "100,000 - 150,000 km", "count": queryset.filter(mileage__range=(100000, 150000)).count()},
                {"value": "150000-200000", "label": "150,000 - 200,000 km", "count": queryset.filter(mileage__range=(150000, 200000)).count()},
                {"value": "200000-", "label": "Over 200,000 km", "count": queryset.filter(mileage__gt=200000).count()}
            ]
            filter_config[key] = {"type": "checkbox", "options": opts}
        elif key == "created_at":
            opts = [
                {
                    "value": str(today),
                    "label": "Today",
                    "count": queryset.filter(created_at__date=today).count()
                },
                {
                    "value": f"{last_3_days}-{today}",
                    "label": "Last 3 Days",
                    "count": queryset.filter(created_at__date__range=[last_3_days, today]).count()
                },
                {
                    "value": f"{last_week}-{today}",
                    "label": "Last Week",
                    "count": queryset.filter(created_at__date__range=[last_week, today]).count()
                },
                {
                    "value": f"{last_month}-{today}",
                    "label": "Last Month",
                    "count": queryset.filter(created_at__date__range=[last_month, today]).count()
                }
            ]
            filter_config[key] = {"type": "button", "options": opts}
        else:
            values = queryset.values(key).annotate(count=Count('pk'))
            opts = [
                {"value": v, "label": v, "count": cnt}
                for v, cnt in [(entry[key] if entry[key] is not None else 'None', entry['count']) for entry in values]
            ]
            filter_config[key] = {"type": "dropdown", "options": opts}
    return filter_config

class CarFilteredList(APIView):
    """
    Returns a filtered list of cars, with dynamic allowed filters based on /api/cars/filters-summary/.
    Also provides filter configuration for client UI with dynamic counts.
    """
    def get(self, request):
        # Get filter summary for allowed filters
        summary_view = CarFiltersSummary()
        summary_response = summary_view.get(request)
        summary_data = summary_response.data if hasattr(summary_response, 'data') else summary_response
        logger.debug(f"Summary data: {summary_data}")

        # Define allowed filters, including price, mileage, and created_at
        allowed = []
        for key, value_counts in summary_data.items():
            if len(value_counts) > 1 or key in ['year', 'created_at']:
                allowed.append(key)
        allowed.extend(['price', 'mileage'])

        # Log raw query parameters for debugging
        logger.info(f"Raw query params: {request.query_params}")

        # Build filters from request
        filters = {}
        for key in allowed:
            value = request.query_params.get(key)
            if value:
                if key in ['price', 'mileage'] and '-' in value:
                    min_val, max_val = value.split('-')
                    min_val = int(min_val) if min_val else None
                    max_val = int(max_val) if max_val else None
                    if min_val is not None and max_val is not None:
                        filters[f'{key}__range'] = (min_val, max_val)
                    elif min_val is not None:
                        filters[f'{key}__gte'] = min_val
                    elif max_val is not None:
                        filters[f'{key}__lte'] = max_val
                elif key == 'year' and '-' in value:
                    start_year, end_year = value.split('-')
                    try:
                        start_year = int(start_year) if start_year else None
                        end_year = int(end_year) if end_year else None
                        if start_year and end_year:
                            filters['year__range'] = (start_year, end_year)
                        elif start_year:
                            filters['year__gte'] = start_year
                        elif end_year:
                            filters['year__lte'] = end_year
                    except ValueError:
                        logger.error(f"Invalid year range: {value}")
                        continue
                elif key == 'created_at':
                    logger.info(f"Received created_at raw value: '{value}'")
                    try:
                        # Normalize input by stripping whitespace
                        value = value.strip()
                        # Validate format with regex
                        import re
                        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
                        range_pattern = r'^(\d{4}-\d{2}-\d{2})-(\d{4}-\d{2}-\d{2})$'
                        range_match = re.match(range_pattern, value)
                        if range_match:
                            # Range filter: YYYY-MM-DD-YYYY-MM-DD
                            start_date_str, end_date_str = range_match.groups()
                            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=dt_timezone.utc)
                            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=dt_timezone.utc, hour=23, minute=59, second=59)
                            if start_date > end_date:
                                raise ValueError(f"Invalid created_at range: start date {start_date_str} is after end date {end_date_str}")
                            filters['created_at__range'] = (start_date, end_date)
                        elif re.match(date_pattern, value):
                            # Single date filter: YYYY-MM-DD
                            date = datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=dt_timezone.utc)
                            filters['created_at__range'] = (date, date.replace(hour=23, minute=59, second=59))
                        else:
                            raise ValueError(f"Invalid created_at format: {value}")
                        logger.info(f"Parsed created_at: {value}, Start: {filters['created_at__range'][0]}, End: {filters['created_at__range'][1]}")
                    except ValueError as e:
                        logger.error(f"Invalid created_at format: {value}, Error: {str(e)}")
                        continue
                elif key == 'year':
                    try:
                        filters['year'] = int(value)
                    except ValueError:
                        logger.error(f"Invalid year value: {value}")
                        continue
                elif value.lower() == 'none' and key in ['fuel_type', 'gear_type']:
                    filters[f'{key}__isnull'] = True
                else:
                    filters[key] = value

        # Apply filters to get the filtered queryset for results
        results_queryset = Car.objects.filter(**filters).order_by('-created_at')
        serializer = CarShortSerializer(results_queryset, many=True)

        # For filter config, remove created_at__range filter (if present) to get all available options
        filter_filters = dict(filters)  # shallow copy
        filter_filters.pop('created_at__range', None)
        filter_queryset = Car.objects.filter(**filter_filters)

        # Log filtered queryset count for debugging
        logger.info(f"Filtered queryset count: {results_queryset.count()}")

        # Build filter config with dynamic counts based on filter_queryset (not results_queryset)
        filter_config = build_filter_config(filter_queryset, allowed)

        return Response({
            "results": serializer.data,
            "filters": filter_config,
        })
    

# DropdownOptions API view for categorical field unique values
class DropdownOptions(APIView):
    def get(self, request):
        fields = ['brand', 'model', 'color', 'gear_type', 'fuel_type', 'body_type']
        result = {}
        for field in fields:
            values = Car.objects.values_list(field, flat=True).distinct()
            result[field] = sorted(list(filter(None, set(values))))
        return Response(result)


class BrandModels(APIView):
    """Return {brand: [model, ...]} mapping so the UI can filter models by brand."""
    def get(self, request):
        pairs = (
            Car.objects.filter(brand__isnull=False, model__isnull=False)
            .values_list('brand', 'model')
            .distinct()
        )
        result = {}
        for brand, model in pairs:
            result.setdefault(brand, [])
            if model not in result[brand]:
                result[brand].append(model)
        for brand in result:
            result[brand].sort()
        return Response(result)


class PriceHistory(APIView):
    """Monthly price trend for a specific car spec.

    When `mileage` is supplied, uses hedonic regression:
      - Takes ALL listings (no mileage filter)
      - Computes one pooled price-per-km slope across all months
      - Per month: price_at_mileage = avg_price + slope × (avg_km − user_km)
      - This answers: "what would MY exact car have cost each month?"

    Without `mileage`, returns plain monthly averages.

    Required: brand, model
    Optional: year, gear_type, color, mileage
    """
    def get(self, request):
        brand      = request.query_params.get('brand')
        model_name = request.query_params.get('model')
        if not brand or not model_name:
            return Response({"error": "brand and model are required"}, status=400)

        since = timezone.now() - timedelta(days=400)
        qs = Car.objects.filter(
            brand=brand, model=model_name,
            price__gt=0, price__lt=500000,
            mileage__gt=500, mileage__lt=500000,
            created_at__gte=since,
        )
        if request.query_params.get('year'):
            qs = qs.filter(year=int(request.query_params['year']))
        if request.query_params.get('gear_type'):
            qs = qs.filter(gear_type=request.query_params['gear_type'])
        if request.query_params.get('color'):
            qs = qs.filter(color=request.query_params['color'])

        user_mileage_raw = request.query_params.get('mileage')

        if user_mileage_raw:
            # ── Hedonic mode ──────────────────────────────────────────────
            user_km = int(user_mileage_raw)

            # Pooled slope across all months (stable, not per-month noise)
            rows_all = list(qs.values_list('price', 'mileage'))
            if len(rows_all) >= 10:
                prices   = [float(r[0]) for r in rows_all]
                kms      = [float(r[1]) for r in rows_all]
                n        = len(rows_all)
                mean_p   = sum(prices) / n
                mean_km  = sum(kms) / n
                cov      = sum((p - mean_p) * (k - mean_km) for p, k in zip(prices, kms)) / n
                var_km   = sum((k - mean_km) ** 2 for k in kms) / n
                slope    = cov / var_km if var_km > 0 else 0.0
            else:
                slope = 0.0

            monthly = (
                qs.annotate(month=TruncMonth('created_at'))
                .values('month')
                .annotate(avg_price=Avg('price'), avg_km=Avg('mileage'), count=Count('car_id'))
                .order_by('month')
            )
            data = []
            for r in monthly:
                adj = round(float(r['avg_price']) + slope * (user_km - float(r['avg_km'])))
                data.append({
                    "month":            r['month'].strftime('%Y-%m'),
                    "avg_price":        round(r['avg_price']),
                    "price_at_mileage": adj,
                    "avg_km":           round(r['avg_km']),
                    "count":            r['count'],
                })
            return Response({
                "data":         data,
                "hedonic":      True,
                "pooled_slope": round(slope, 6),
                "user_km":      user_km,
            })

        # ── Plain mode (no mileage param) ─────────────────────────────────
        rows = (
            qs.annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(avg_price=Avg('price'), count=Count('car_id'))
            .order_by('month')
        )
        data = [
            {"month": r['month'].strftime('%Y-%m'),
             "avg_price": round(r['avg_price']),
             "count":     r['count']}
            for r in rows
        ]
        return Response({"data": data})


class SmartPrice(APIView):
    """Current market price for a car spec + mileage.

    Searches the same mileage band that will be shown on the chart,
    so the price message and trend chart always show identical data.

    Tries progressively wider bands/windows until ≥ MIN_LISTINGS found.
    Returns mileage_low + mileage_high so the bot can pass them to
    PriceHistory for a consistent chart.

    Required: brand, model, year, gear_type, color, mileage
    """
    MIN_LISTINGS = 5
    # Junk filter: excludes typos and "first instalment" scam prices that would
    # otherwise poison the min/median for expensive cars.
    PRICE_FLOOR = 1500
    PRICE_CEIL  = 300000

    def get(self, request):
        try:
            brand      = request.query_params['brand']
            model_name = request.query_params['model']
            year       = int(request.query_params['year'])
            gear_type  = request.query_params['gear_type']
            color      = request.query_params['color']
            mileage    = int(request.query_params['mileage'])
        except (KeyError, ValueError):
            return Response(
                {"error": "brand, model, year, gear_type, color, mileage all required"},
                status=400,
            )

        clean = Car.objects.filter(
            brand=brand, model=model_name, year=year,
            price__gte=self.PRICE_FLOOR, price__lte=self.PRICE_CEIL,
        )

        # Tiers relax the spec from exact → looser so we stay on REAL market
        # data as long as possible. The ML fallback badly under-prices rare /
        # expensive models (it was trained on cheap high-volume cars), so we
        # only surrender to it after exhausting genuine comparables.
        #   spec_filter: extra Django filters on top of brand+model+year
        #   days: recency window · band: ± mileage fraction
        #   min_n: how many real listings this tier needs to be trusted
        #   match: human label of how relaxed the match is
        tiers = [
            (dict(gear_type=gear_type, color=color), 30, 0.25, 5, "exact"),
            (dict(gear_type=gear_type, color=color), 90, 0.35, 5, "exact"),
            (dict(gear_type=gear_type),              90, 0.35, 4, "any color"),
            (dict(),                                 90, 0.40, 4, "any color/gear"),
            (dict(),                                180, 0.50, 3, "any color/gear"),
            (dict(),                                180, 1.00, 3, "any mileage"),
        ]

        for spec_filter, days, band, min_n, match in tiers:
            low  = max(0, int(mileage * (1 - band)))
            high = int(mileage * (1 + band))
            qs = clean.filter(
                **spec_filter,
                mileage__gte=low, mileage__lte=high,
                created_at__gte=timezone.now() - timedelta(days=days),
            )
            prices = sorted(qs.values_list('price', flat=True))
            if len(prices) >= min_n:
                median = prices[len(prices) // 2]
                return Response({
                    "price":        round(median),
                    "avg":          round(sum(prices) / len(prices)),
                    "min":          round(prices[0]),
                    "max":          round(prices[-1]),
                    "source":       f"market_{days}d",
                    "count":        len(prices),
                    "period":       f"last {days} days",
                    "match":        match,
                    "mileage_band": f"{low:,}–{high:,} km",
                    "mileage_low":  low,
                    "mileage_high": high,
                })

        # Truly no comparable real listings anywhere — let the caller try ML,
        # but hand back the brand+model+year price envelope so the caller can
        # sanity-clamp the ML number instead of trusting it blindly.
        envelope = list(
            clean.values_list('price', flat=True)
        )
        low  = int(mileage * 0.75)
        high = int(mileage * 1.25)
        payload = {
            "price":        None,
            "source":       "insufficient_data",
            "count":        len(envelope),
            "mileage_low":  low,
            "mileage_high": high,
        }
        if envelope:
            envelope.sort()
            payload["envelope_min"]    = round(envelope[0])
            payload["envelope_max"]    = round(envelope[-1])
            payload["envelope_median"] = round(envelope[len(envelope) // 2])
        return Response(payload)


# ─────────────────────────────────────────────────────────────────────────────
# Channel analytics endpoints
# ─────────────────────────────────────────────────────────────────────────────

class BrandRanking(APIView):
    """Top brands by listing count for the last N days, with week-over-week change.

    Query params: days (default 7), top (default 10)
    """
    def get(self, request):
        days = int(request.query_params.get('days', 7))
        top  = int(request.query_params.get('top', 10))
        now  = timezone.now()
        since      = now - timedelta(days=days)
        prev_since = since - timedelta(days=days)

        current_qs = (
            Car.objects.filter(created_at__gte=since, price__gt=0)
            .values('brand')
            .annotate(count=Count('car_id'), avg_price=Avg('price'))
            .order_by('-count')[:top]
        )
        prev_counts = {
            r['brand']: r['count']
            for r in Car.objects.filter(
                created_at__gte=prev_since, created_at__lt=since, price__gt=0
            ).values('brand').annotate(count=Count('car_id'))
        }

        result = []
        for r in current_qs:
            prev = prev_counts.get(r['brand'], 0)
            pct  = round((r['count'] - prev) / prev * 100, 1) if prev > 0 else None
            result.append({
                'brand':      r['brand'],
                'count':      r['count'],
                'avg_price':  round(float(r['avg_price'])),
                'prev_count': prev,
                'pct_change': pct,
            })
        return Response({'period_days': days, 'brands': result})


class PriceMovers(APIView):
    """Models with the biggest price change vs the previous period.

    Query params: days (default 7), min_count (default 5), top (default 5)
    """
    def get(self, request):
        days      = int(request.query_params.get('days', 7))
        min_count = int(request.query_params.get('min_count', 5))
        top       = int(request.query_params.get('top', 5))
        now       = timezone.now()
        since      = now - timedelta(days=days)
        prev_since = since - timedelta(days=days)

        current = {
            (r['brand'], r['model']): {'avg': float(r['avg_price']), 'count': r['count']}
            for r in Car.objects.filter(created_at__gte=since, price__gt=0)
                .values('brand', 'model')
                .annotate(avg_price=Avg('price'), count=Count('car_id'))
                .filter(count__gte=min_count)
        }
        prev = {
            (r['brand'], r['model']): float(r['avg_price'])
            for r in Car.objects.filter(
                created_at__gte=prev_since, created_at__lt=since, price__gt=0
            ).values('brand', 'model').annotate(avg_price=Avg('price'))
        }

        movers = []
        for (brand, model), curr in current.items():
            if (brand, model) in prev and prev[(brand, model)] > 0:
                pct = (curr['avg'] - prev[(brand, model)]) / prev[(brand, model)] * 100
                movers.append({
                    'brand':          brand,
                    'model':          model,
                    'avg_price':      round(curr['avg']),
                    'prev_avg_price': round(prev[(brand, model)]),
                    'change_pct':     round(pct, 1),
                    'count':          curr['count'],
                })

        movers.sort(key=lambda x: x['change_pct'])
        return Response({
            'period_days': days,
            'fallers':     movers[:top],
            'risers':      list(reversed(movers[-top:])),
        })


class WeeklyDigest(APIView):
    """Full weekly market summary for the channel digest post."""
    def get(self, request):
        now        = timezone.now()
        since      = now - timedelta(days=7)
        since_year = now - timedelta(days=365)
        year_window = timedelta(days=30)  # wider window for year-ago comparison

        total = Car.objects.filter(created_at__gte=since).count()

        brand_rows = (
            Car.objects.filter(created_at__gte=since, price__gt=0)
            .values('brand')
            .annotate(count=Count('car_id'), avg_price=Avg('price'))
            .order_by('-count')[:10]
        )

        top_brands = []
        for row in brand_rows:
            brand_name = row['brand']

            # Top 5 models for this brand: count + min/max/avg price
            model_rows = (
                Car.objects.filter(brand=brand_name, created_at__gte=since, price__gt=0)
                .values('model')
                .annotate(
                    count=Count('car_id'),
                    avg_price=Avg('price'),
                    min_price=Min('price'),
                    max_price=Max('price'),
                )
                .order_by('-count')[:5]
            )

            models = []
            for m in model_rows:
                model_name = m['model']
                avg_p = float(m['avg_price'])

                # 10th–90th percentile range: excludes crashed/damaged (low) and overpriced/modified (high)
                with connection.cursor() as cur:
                    cur.execute("""
                        SELECT
                            PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY price),
                            PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY price)
                        FROM marketplace.cars
                        WHERE brand = %s AND model = %s
                          AND created_at >= %s AND price > 0
                    """, [brand_name, model_name, since])
                    pct = cur.fetchone()
                min_price = round(float(pct[0])) if pct and pct[0] else round(avg_p)
                max_price = round(float(pct[1])) if pct and pct[1] else round(avg_p)

                # YoY: same brand+model, now vs ~1 year ago
                qs_year = Car.objects.filter(
                    brand=brand_name, model=model_name,
                    created_at__gte=since_year,
                    created_at__lt=since_year + year_window,
                    price__gt=0,
                )
                qs_now = Car.objects.filter(
                    brand=brand_name, model=model_name,
                    created_at__gte=since, price__gt=0,
                )
                avg_now  = qs_now.aggregate(a=Avg('price'))['a']
                avg_year = qs_year.aggregate(a=Avg('price'))['a']
                yoy_pct = None
                year_ago_price = None
                if avg_now and avg_year:
                    yoy_pct = round((float(avg_now) - float(avg_year)) / float(avg_year) * 100, 1)
                    year_ago_price = round(float(avg_year))

                models.append({
                    'model':          model_name,
                    'count':          m['count'],
                    'avg_price':      round(avg_p),
                    'min_price':      min_price,
                    'max_price':      max_price,
                    'yoy_pct':        yoy_pct,
                    'year_ago_price': year_ago_price,
                })

            top_brands.append({
                'brand':     brand_name,
                'count':     row['count'],
                'avg_price': round(float(row['avg_price'])),
                'models':    models,
            })

        return Response({
            'total_listings': total,
            'top_brands':     top_brands,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Admin / channel post config
# ─────────────────────────────────────────────────────────────────────────────

class PostConfig(APIView):
    """GET all channel post configs; PATCH {post_type} to toggle enabled."""
    def get(self, request):
        with connection.cursor() as cur:
            cur.execute("""
                SELECT post_type, name, description, enabled, schedule,
                       to_char(last_posted, 'DD.MM.YYYY HH24:MI') AS last_posted
                FROM marketplace.channel_post_config
                ORDER BY enabled DESC, post_type
            """)
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return Response(rows)

    def patch(self, request, post_type):
        enabled = request.data.get('enabled')
        if enabled is None:
            return Response({'error': 'enabled required'}, status=400)
        with connection.cursor() as cur:
            cur.execute("""
                UPDATE marketplace.channel_post_config
                SET enabled = %s WHERE post_type = %s
                RETURNING post_type, enabled
            """, [bool(enabled), post_type])
            result = cur.fetchone()
        if not result:
            return Response({'error': 'not found'}, status=404)
        return Response({'post_type': result[0], 'enabled': result[1]})


class ColorPremium(APIView):
    def get(self, request):
        since = timezone.now() - timedelta(days=30)
        qs = Car.objects.filter(created_at__gte=since, price__gt=0).exclude(color__in=['', None])
        overall = qs.aggregate(a=Avg('price'))['a']
        rows = (qs.values('color')
                  .annotate(count=Count('car_id'), avg_price=Avg('price'))
                  .filter(count__gte=15)
                  .order_by('-avg_price')[:8])
        colors = []
        for r in rows:
            avg = float(r['avg_price'])
            pct = round((avg - float(overall)) / float(overall) * 100, 1) if overall else 0
            colors.append({'color': r['color'], 'count': r['count'],
                           'avg_price': round(avg), 'vs_market_pct': pct})
        return Response({'colors': colors, 'market_avg': round(float(overall)) if overall else 0})


class GearPremium(APIView):
    def get(self, request):
        since = timezone.now() - timedelta(days=30)
        top_brands = [r['brand'] for r in (
            Car.objects.filter(created_at__gte=since, price__gt=0)
            .values('brand').annotate(c=Count('car_id')).order_by('-c')[:6]
        )]
        brands_data = []
        for brand in top_brands:
            qs = Car.objects.filter(brand=brand, created_at__gte=since, price__gt=0)
            at = qs.filter(gear_type='Automatic').aggregate(a=Avg('price'), c=Count('car_id'))
            mt = qs.filter(gear_type='Manual').aggregate(a=Avg('price'), c=Count('car_id'))
            if at['a'] and mt['a'] and at['c'] >= 3 and mt['c'] >= 3:
                brands_data.append({
                    'brand': brand,
                    'at_price': round(float(at['a'])), 'at_count': at['c'],
                    'mt_price': round(float(mt['a'])), 'mt_count': mt['c'],
                    'premium_pct': round((float(at['a']) - float(mt['a'])) / float(mt['a']) * 100, 1),
                })
        return Response({'brands': sorted(brands_data, key=lambda x: abs(x['premium_pct']), reverse=True)})


class AgeDepreciation(APIView):
    """Depreciation curve for a SINGLE model — median price by model-year.

    Why per-model, not per-brand: averaging a Chevrolet Tahoe and a Spark of
    the same year together is meaningless. A curve is only interpretable for
    one model. Uses MEDIAN (robust to outliers) and a junk filter.

    Query params:
      brand, model  — if given, returns that model's curve
      (default)     — returns curves for a set of high-volume popular models
    """
    DEFAULT_MODELS = [
        ('Chevrolet', 'Cobalt'), ('Chevrolet', 'Nexia'), ('Chevrolet', 'Malibu'),
        ('Chevrolet', 'Lacetti'), ('Chevrolet', 'Onix'),
    ]

    def _curve(self, brand, model):
        with connection.cursor() as cur:
            cur.execute("""
                SELECT year,
                       COUNT(*) AS cnt,
                       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price))::int AS median_price
                FROM marketplace.cars
                WHERE brand = %s AND model = %s
                  AND price BETWEEN 1500 AND 200000
                  AND mileage BETWEEN 0 AND 400000
                  AND year BETWEEN 2010 AND 2025
                GROUP BY year
                HAVING COUNT(*) >= 10
                ORDER BY year
            """, [brand, model])
            years = [
                {'year': r[0], 'count': r[1], 'median_price': r[2]}
                for r in cur.fetchall()
            ]
        return years

    def get(self, request):
        brand = request.query_params.get('brand')
        model = request.query_params.get('model')
        if brand and model:
            pairs = [(brand, model)]
        else:
            pairs = self.DEFAULT_MODELS
        result = []
        for b, m in pairs:
            years = self._curve(b, m)
            if len(years) >= 3:
                first, last = years[0], years[-1]
                span = last['year'] - first['year']
                drop_pct = (
                    round((last['median_price'] - first['median_price'])
                          / last['median_price'] * 100)
                    if last['median_price'] else None
                )
                result.append({
                    'brand': b, 'model': m, 'years': years,
                    'span_years': span, 'total_drop_pct': drop_pct,
                })
        return Response({'models': result})


class BestValue(APIView):
    """Genuinely underpriced listings this week.

    Correctness safeguards (vs the old naive version that surfaced wrecks and
    down-payment scams):
      - Peers are matched on {brand, model, year, MILEAGE BAND}, not just year,
        so a high-mileage car isn't flagged "cheap" against low-mileage peers.
      - Compares against the peer MEDIAN (robust), requires >= 15 peers.
      - Junk filter: price 2000-150000, mileage 1000-300000 (drops typos,
        parts cars, and "first instalment" scam prices).
      - Discount is capped: a real private deal is ~15-35% under median.
        Anything cheaper than DISCOUNT_CAP is almost always an instalment
        down-payment or a damaged car, so it is excluded, not celebrated.
    """
    DISCOUNT_FLOOR = 12   # must be at least this % under peer median to qualify
    DISCOUNT_CAP   = 38   # more than this % under median → almost certainly a scam

    def get(self, request):
        since = timezone.now() - timedelta(days=7)
        with connection.cursor() as cur:
            cur.execute("""
                WITH clean AS (
                    SELECT brand, model, year, price::int AS price, mileage,
                           reference_url,
                           width_bucket(mileage, 0, 300000, 6) AS km_band
                    FROM marketplace.cars
                    WHERE created_at >= %s
                      AND price BETWEEN 2000 AND 150000
                      AND mileage BETWEEN 1000 AND 300000
                ),
                peer AS (
                    SELECT brand, model, year, km_band,
                           PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price) AS med,
                           COUNT(*) AS peers
                    FROM clean
                    GROUP BY brand, model, year, km_band
                    HAVING COUNT(*) >= 15
                )
                SELECT c.brand, c.model, c.year, c.price, c.mileage,
                       c.reference_url,
                       p.med::int AS median_price,
                       ROUND((p.med - c.price) / p.med * 100)::int AS discount_pct
                FROM clean c
                JOIN peer p USING (brand, model, year, km_band)
                WHERE (p.med - c.price) / p.med * 100 BETWEEN %s AND %s
                ORDER BY discount_pct DESC
                LIMIT 10
            """, [since, self.DISCOUNT_FLOOR, self.DISCOUNT_CAP])
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return Response({'listings': rows, 'period_days': 7})


class GearPriceSplit(APIView):
    """Median/min/max price for a model, split by transmission, last N days.

    Powers the vertical "shorts" price cards (manual vs automatic). Median +
    10th–90th percentile range so a couple of scam/outlier prices don't stretch
    the band. Junk filter drops instalment down-payment listings.

    Query params: brand, model, days (default 7).
    """
    GEAR_LABEL = {'AT': 'Automatic', 'MT': 'Manual', 'DSG': 'Dual-clutch', 'CVT': 'CVT'}

    def get(self, request):
        brand = request.query_params.get('brand', 'Chevrolet')
        model = request.query_params.get('model', 'Spark')
        try:
            days = int(request.query_params.get('days', 7))
        except (TypeError, ValueError):
            days = 7
        with connection.cursor() as cur:
            cur.execute("""
                SELECT gear_type,
                       COUNT(*) AS cnt,
                       ROUND(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY price))::int AS median,
                       ROUND(PERCENTILE_CONT(0.1)  WITHIN GROUP (ORDER BY price))::int AS low,
                       ROUND(PERCENTILE_CONT(0.9)  WITHIN GROUP (ORDER BY price))::int AS high
                FROM marketplace.cars
                WHERE brand = %s AND model = %s
                  AND gear_type IN ('AT', 'MT', 'DSG', 'CVT')
                  AND price BETWEEN 1500 AND 200000
                  AND mileage BETWEEN 0 AND 400000
                  AND created_at >= NOW() - INTERVAL '1 day' * %s
                GROUP BY gear_type
                HAVING COUNT(*) >= 3
                ORDER BY median
            """, [brand, model, days])
            gears = [
                {'gear': r[0], 'label': self.GEAR_LABEL.get(r[0], r[0]),
                 'count': r[1], 'median': r[2], 'low': r[3], 'high': r[4]}
                for r in cur.fetchall()
            ]
        return Response({'brand': brand, 'model': model, 'days': days, 'gears': gears})


class SeasonalTrends(APIView):
    """Cheapest / priciest month to buy a SINGLE model — monthly median.

    Per-model (not per-brand) and MEDIAN so the trend reflects real price
    level, not a shifting mix of models within a brand. Holding the model
    fixed, month-to-month median movement is a genuine seasonal signal.

    Query params: brand, model (default: a high-volume popular model).
    """
    def get(self, request):
        brand = request.query_params.get('brand', 'Chevrolet')
        model = request.query_params.get('model', 'Cobalt')
        with connection.cursor() as cur:
            cur.execute("""
                SELECT to_char(date_trunc('month', created_at), 'YYYY-MM') AS month,
                       COUNT(*) AS cnt,
                       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price))::int AS median_price
                FROM marketplace.cars
                WHERE brand = %s AND model = %s
                  AND price BETWEEN 1500 AND 200000
                  AND mileage BETWEEN 0 AND 400000
                GROUP BY 1
                HAVING COUNT(*) >= 15
                ORDER BY 1
            """, [brand, model])
            months = [
                {'month': r[0], 'count': r[1], 'median_price': r[2]}
                for r in cur.fetchall()
            ]
        cheapest = min(months, key=lambda m: m['median_price']) if months else None
        priciest = max(months, key=lambda m: m['median_price']) if months else None
        return Response({
            'brand': brand, 'model': model, 'months': months,
            'cheapest_month': cheapest, 'priciest_month': priciest,
        })


class MarketBreadth(APIView):
    def get(self, request):
        since = timezone.now() - timedelta(days=7)
        bands = [
            ('Under $5k',   0,     5000),
            ('$5k-$10k',   5000,  10000),
            ('$10k-$20k', 10000,  20000),
            ('$20k-$30k', 20000,  30000),
            ('Over $30k',  30000, 9999999),
        ]
        result = []
        for label, low, high in bands:
            count = Car.objects.filter(
                created_at__gte=since, price__gt=low, price__lte=high).count()
            result.append({'label': label, 'count': count, 'low': low, 'high': high})
        total = sum(b['count'] for b in result)
        for b in result:
            b['pct'] = round(b['count'] / total * 100, 1) if total else 0
        return Response({'bands': result, 'total': total})


class MileageDepreciation(APIView):
    def get(self, request):
        top_models = [
            ('Chevrolet', 'Lacetti'), ('Chevrolet', 'Cobalt'), ('Chevrolet', 'Spark'),
            ('BYD', 'Song'), ('Hyundai', 'Elantra'), ('Kia', 'Sportage'),
        ]
        result = []
        for brand, model in top_models:
            rows = list(
                Car.objects.filter(brand=brand, model=model, price__gt=0, mileage__gt=0)
                .values_list('price', 'mileage')
            )
            if len(rows) < 15:
                continue
            prices = [float(r[0]) for r in rows]
            kms    = [float(r[1]) for r in rows]
            n = len(rows)
            mp, mk = sum(prices)/n, sum(kms)/n
            cov = sum((p-mp)*(k-mk) for p,k in zip(prices,kms)) / n
            var = sum((k-mk)**2 for k in kms) / n
            slope = cov/var if var > 0 else 0
            result.append({'brand': brand, 'model': model,
                           'price_per_10k_km': round(slope * 10000),
                           'count': n, 'avg_price': round(mp)})
        return Response({'models': sorted(result, key=lambda x: x['price_per_10k_km'])})


class ScraperRunsView(APIView):
    """
    GET  /api/scraper-runs/          → latest run per scraper+category
    POST /api/scraper-runs/          → start a new run, returns {id}
    """
    def get(self, request):
        with connection.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (scraper_name, COALESCE(category, ''))
                    id, scraper_name, category,
                    started_at, finished_at, status,
                    pages_scraped, new_records, total_records, early_stopped, error_msg
                FROM marketplace.scraper_runs
                ORDER BY scraper_name, COALESCE(category, ''), started_at DESC
            """)
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return Response(rows)

    def post(self, request):
        name = request.data.get('scraper_name', '')
        cat  = request.data.get('category')
        if not name:
            return Response({'error': 'scraper_name required'}, status=400)
        with connection.cursor() as cur:
            cur.execute("""
                INSERT INTO marketplace.scraper_runs (scraper_name, category, status)
                VALUES (%s, %s, 'running') RETURNING id
            """, [name, cat])
            run_id = cur.fetchone()[0]
        return Response({'id': run_id}, status=201)


class ScraperRunDetailView(APIView):
    """PATCH /api/scraper-runs/{id}/ → update progress or mark completed/error"""
    def patch(self, request, run_id):
        allowed = ('status', 'pages_scraped', 'new_records', 'total_records',
                   'early_stopped', 'finished_at', 'error_msg')
        fields = [(k, request.data[k]) for k in allowed if k in request.data]
        if not fields:
            return Response({'error': 'no fields'}, status=400)
        set_clause = ', '.join(f"{k} = %s" for k, _ in fields)
        values = [v for _, v in fields] + [run_id]
        with connection.cursor() as cur:
            cur.execute(
                f"UPDATE marketplace.scraper_runs SET {set_clause} WHERE id = %s",
                values,
            )
        return Response({'ok': True})


import re as _re

def _normalize_iphone_model(raw: str) -> str:
    """iPhone 12Pro Max → iPhone 12 Pro Max."""
    s = raw.strip()
    s = _re.sub(r'(\d)(Pro|Mini|Plus|Max)', r'\1 \2', s)
    s = _re.sub(r'(Pro)(Max)', r'\1 \2', s)
    s = _re.sub(r'\s+', ' ', s)
    return s


def _normalize_macbook_model(raw: str) -> str:
    """
    Canonical form: MacBook [Air|Pro] [chip]
      MacBook M1 PRO        → MacBook Pro M1
      MacBook M2 PRO        → MacBook Pro M2
      MacBook M3 MAX        → MacBook Pro M3 Max
      MacBook M4 MAX        → MacBook Pro M4 Max
      MacBook Air M1        → MacBook Air M1
      MacBook Air M4 MAX    → MacBook Air M4 Max   (chip from specs)
      MacBook Pro M4 PRO    → MacBook Pro M4 Pro   (chip from specs)
      MacBook Pro M3 MAX    → MacBook Pro M3 Max
      MacBook Air (Intel)   → MacBook Air (Intel)
      MacBook Air M5        → MacBook Air M5
    """
    s = raw.strip()
    # Title-case chip qualifiers ("M4 MAX" → "M4 Max", "M4 PRO" → "M4 Pro")
    s = _re.sub(r'\bPRO\b', 'Pro', s)
    s = _re.sub(r'\bMAX\b', 'Max', s)
    # Bare-chip titles without Air/Pro segment default to the Pro line:
    # "MacBook M1 Pro" / "MacBook M2 Pro" → "MacBook Pro M1/M2"
    s = _re.sub(r'^MacBook\s+(M\d)\s+Pro$', r'MacBook Pro \1', s)
    # "MacBook M3 Max" / "MacBook M4 Max" → "MacBook Pro M3/M4 Max"
    s = _re.sub(r'^MacBook\s+(M\d)\s+Max$', r'MacBook Pro \1 Max', s)
    # Uppercase a lowercase chip prefix recovered from a title ("m5" -> "M5")
    s = _re.sub(r'\bm([1-9])\b', lambda m: 'M' + m.group(1), s)
    s = _re.sub(r'\s+', ' ', s)
    return s


def _normalize_gpu_model(raw: str) -> str:
    """
    Canonical form: [GTX|RTX|RX] [number] [Ti|Super|XT]
      RX580         → RX 580
      RTX3060TI     → RTX 3060 Ti
      GTX 1050 TI   → GTX 1050 Ti
      RTX2060SUPER  → RTX 2060 Super
      RX 5700XT     → RX 5700 XT
      RX9070XT      → RX 9070 XT
    """
    s = raw.strip()
    # Uppercase the series prefix
    s = _re.sub(r'\b(gtx|rtx|rx)\b', lambda m: m.group().upper(), s, flags=_re.IGNORECASE)
    # Insert space between series and number: "RTX3080" → "RTX 3080"
    s = _re.sub(r'(GTX|RTX|RX)(\d)', r'\1 \2', s)
    # Insert space between number and suffix: "3060TI" → "3060 TI"
    s = _re.sub(r'(\d)(TI|SUPER|XT)\b', r'\1 \2', s, flags=_re.IGNORECASE)
    # Normalise suffix case
    s = _re.sub(r'\bTI\b',    'Ti',    s, flags=_re.IGNORECASE)
    s = _re.sub(r'\bSUPER\b', 'Super', s, flags=_re.IGNORECASE)
    s = _re.sub(r'\bxt\b',    'XT',    s, flags=_re.IGNORECASE)
    s = _re.sub(r'\s+', ' ', s)
    return s


def _normalize_ssd_model(raw: str) -> str:
    """NVMe 512GB, SATA 1TB — keep interface + capacity."""
    s = raw.strip().upper()
    s = _re.sub(r'ГБ', 'GB', s)
    s = _re.sub(r'ТБ', 'TB', s)
    s = _re.sub(r'\bM\.2\b|\bPCIE\b', 'NVMe', s)
    s = _re.sub(r'\s+', ' ', s)
    return s.strip()


def _normalize_ram_model(raw: str) -> str:
    """Group by DDR generation + total capacity, stripping speeds (MHz).

    DDR4 3200      → DDR4        (3200 is a speed, no GB suffix)
    DDR4 3200 8GB  → DDR4 8GB    (strip speed, keep capacity)
    DDR4 2         → DDR4        (truncated kit notation, no GB)
    DDR4 2x8GB     → DDR4 16GB   (kit: 2 x 8 = 16)
    DDR 3 8GB      → DDR3 8GB    (fix spurious space)
    DDR5 5600      → DDR5        (5600 is a speed, no GB suffix)
    """
    s = raw.strip().upper()
    s = s.replace('ГБ', 'GB').replace('МГЦ', 'MHZ')
    # Fix "DDR 3" → "DDR3", "DDR 4" → "DDR4"
    s = _re.sub(r'\bDDR\s+([2345])\b', r'DDR\1', s)
    # Extract DDR generation
    gen_m = _re.search(r'DDR([2345]?)', s)
    gen = gen_m.group(1) if gen_m and gen_m.group(1) else ''
    # Kit notation: 2x8GB → 16GB, 2x16GB → 32GB
    kit = _re.search(r'(\d+)\s*[Xx]\s*(\d+)\s*GB', s)
    if kit:
        total = int(kit.group(1)) * int(kit.group(2))
        if total <= 512:
            return f"DDR{gen} {total}GB"
    # Plain capacity: 8GB, 16GB — must be ≤512 to exclude speeds (1600/3200/5600)
    cap = _re.search(r'(\d+)\s*GB', s)
    if cap:
        n = int(cap.group(1))
        if n <= 512:
            return f"DDR{gen} {n}GB"
    # Fallback: just the generation type
    return f"DDR{gen}" if gen else 'RAM'


def _normalize_cpu_model(raw: str) -> str:
    """Intel Core I5-12400 → Intel Core i5-12400 | AMD Ryzen 5 5600X → AMD Ryzen 5 5600X"""
    s = raw.strip()
    # Normalize iX casing: "I5-" or "I5 " → "i5-"
    s = _re.sub(r'\bI([3579])([\s\-])', lambda m: f'i{m.group(1)}-', s)
    # Also catch trailing "I5" with no separator followed by digits: "I5 12400" → "i5-12400"
    s = _re.sub(r'\bi([3579])\s+(\d)', lambda m: f'i{m.group(1)}-{m.group(2)}', s)
    # Uppercase the suffix letters after model number: "i7-14700kf"/"i7-14700Kf" → "i7-14700KF"
    s = _re.sub(r'(i[3579]-\d{4,5})([A-Za-z]+)', lambda m: m.group(1) + m.group(2).upper(), s)
    # Normalize Ryzen casing
    s = _re.sub(r'\bRyzen\b', 'Ryzen', s, flags=_re.IGNORECASE)
    s = _re.sub(r'\bCore\b', 'Core', s, flags=_re.IGNORECASE)
    s = _re.sub(r'\bIntel\b', 'Intel', s, flags=_re.IGNORECASE)
    s = _re.sub(r'\bAMD\b', 'AMD', s, flags=_re.IGNORECASE)
    s = _re.sub(r'\s+', ' ', s)
    return s.strip()


def _normalize_console_model(raw: str) -> str:
    """PlayStation 5 Slim → PlayStation 5 Slim, Xbox Series X → Xbox Series X"""
    s = raw.strip()
    # Expand PS4/PS5 shorthand
    s = _re.sub(r'\bPS([345])\b', r'PlayStation \1', s, flags=_re.IGNORECASE)
    s = _re.sub(r'\s+', ' ', s)
    return s


_NORMALIZERS = {
    'iphone':  _normalize_iphone_model,
    'macbook': _normalize_macbook_model,
    'gpu':     _normalize_gpu_model,
    'ram':     _normalize_ram_model,
    'cpu':     _normalize_cpu_model,
    'console': _normalize_console_model,
    'ssd':     _normalize_ssd_model,
}

# Generic words that are too broad to be useful model names (per category)
_SKIP_MODELS = {
    'iphone':  {'iPhone', 'Apple'},
    'macbook': {'MacBook', 'Apple'},
    'gpu':     {'GPU', 'Видеокарта', 'video karta'},
    'ipad':    {'iPad', 'Apple'},
    'ram':     {'RAM', 'None', 'ОЗУ', 'DDR'},
    'cpu':     {'CPU', 'None', 'Процессор', 'Intel Core', 'AMD Ryzen', 'AMD'},
    'console': {'Console', 'None', 'Приставка', 'Игровая приставка'},
    'ssd':     {'SSD', 'None'},
}


class ElectronicsReport(APIView):
    """
    GET /api/electronics/report/?category=iphone|macbook|gpu|ipad|ram|cpu
    Returns models with p10–p90 price range and listing count.
    """
    MAX_USD   = {
        'iphone':  4000,
        'macbook': 6000,
        'gpu':     3500,
        'ipad':    2000,
        'ram':     500,
        'cpu':     2000,
        'console': 1500,
        'ssd':     800,
    }
    MIN_USD   = {
        'iphone':  50,
        'macbook': 50,
        'gpu':     15,
        'ipad':    50,
        'ram':     5,
        'cpu':     10,
        'console': 20,
        'ssd':     3,
    }
    MIN_COUNT = {
        'iphone':  2,
        'macbook': 2,
        'gpu':     2,
        'ipad':    2,
        'ram':     3,
        'cpu':     2,
        'console': 2,
        'ssd':     2,
    }

    def get(self, request):
        uzs_rate  = _get_uzs_rate()
        category  = request.query_params.get('category', 'iphone')
        max_usd   = self.MAX_USD.get(category, 4000)
        min_usd   = self.MIN_USD.get(category, 50)
        min_count = self.MIN_COUNT.get(category, 2)
        skip      = _SKIP_MODELS.get(category, set())
        normalize = _NORMALIZERS.get(category, lambda x: x.strip())
        try:
            days = int(request.query_params.get('days', 0))
        except (TypeError, ValueError):
            days = 0
        if days < 0:
            days = 0

        with connection.cursor() as cur:
            cur.execute("""
                WITH base AS (
                    SELECT
                        CASE
                          -- 1) chip from structured specs (most reliable)
                          WHEN %s = 'macbook'
                               AND model IN ('MacBook Air', 'MacBook Pro')
                               AND specs IS NOT NULL
                               AND specs->>'chip' IS NOT NULL
                               AND specs->>'chip' != ''
                          THEN model || ' ' || (specs->>'chip')
                          -- 2) chip recovered from the title (e.g. M5 listings the
                          --    scraper mislabelled as Intel) -> "MacBook Pro M5 [Pro|Max]"
                          WHEN %s = 'macbook'
                               AND model IN ('MacBook Air', 'MacBook Pro')
                               AND title ~* '\\mM[1-9]\\M'
                          THEN model || ' '
                               || upper(substring(title from '(?i)\\mM[1-9]\\M'))
                               || COALESCE(
                                    ' ' || initcap((regexp_match(
                                        title, '(?i)M[1-9]\\s*(pro|max)'))[1]),
                                    '')
                          -- 3) genuinely Intel (no chip anywhere)
                          WHEN %s = 'macbook'
                               AND model IN ('MacBook Air', 'MacBook Pro')
                          THEN model || ' (Intel)'
                          -- 4) RAM: model has no GB suffix but specs has capacity
                          --    e.g. model='DDR4 3200', specs capacity_gb=8 → 'DDR4 8GB'
                          --    Only when DDR generation is known AND capacity <= 64GB
                          WHEN %s = 'ram'
                               AND model NOT LIKE '%%GB'
                               AND model NOT LIKE '%%ГБ'
                               AND specs IS NOT NULL
                               AND (specs->>'capacity_gb') IS NOT NULL
                               AND (specs->>'capacity_gb')::int BETWEEN 1 AND 64
                               AND (regexp_match(model, 'DDR\\s*([2-5])'))[1] IS NOT NULL
                          THEN 'DDR' || (regexp_match(model, 'DDR\\s*([2-5])'))[1]
                               || ' ' || (specs->>'capacity_gb')::int || 'GB'
                          -- 5) CPU: resolve bare 'Intel Core'/'AMD Ryzen' labels.
                          --    Prefer structured specs.model_id, then recover the
                          --    model from the title (Core Ultra, iN-NNNN, Xeon).
                          --    Anything still bare falls through to 'Intel Core'/
                          --    'AMD Ryzen'/'AMD' and is dropped via _SKIP_MODELS['cpu'].
                          WHEN %s = 'cpu'
                               AND model IN ('Intel Core', 'AMD Ryzen', 'Intel Xeon', 'AMD')
                          THEN CASE
                                 WHEN specs IS NOT NULL
                                      AND COALESCE(specs->>'model_id', '') != ''
                                   THEN model || ' ' || (specs->>'model_id')
                                 WHEN title ~* '\\multra\\s+[3579]\\s*[0-9]{3}'
                                   THEN 'Intel Core Ultra '
                                        || (regexp_match(title, '(?i)ultra\\s+([3579])\\s*([0-9]{3}[a-z]*)'))[1]
                                        || ' '
                                        || upper((regexp_match(title, '(?i)ultra\\s+([3579])\\s*([0-9]{3}[a-z]*)'))[2])
                                 WHEN title ~* '\\mxeon\\M'
                                   THEN 'Intel Xeon'
                                 WHEN title ~* '\\mi[3579][\\s-]?[0-9]{4}'
                                   THEN 'Intel Core i'
                                        || (regexp_match(title, '(?i)\\mi([3579])[\\s-]?([0-9]{4,5}[a-z]*)'))[1]
                                        || '-'
                                        || upper((regexp_match(title, '(?i)\\mi([3579])[\\s-]?([0-9]{4,5}[a-z]*)'))[2])
                                 ELSE model
                               END
                          ELSE model
                        END AS model,
                        CASE WHEN price_currency = 'USD' THEN price::numeric
                             ELSE price::numeric / %s END AS price_usd,
                        (
                          lower(title) LIKE '%%разбит%%' OR lower(title) LIKE '%%слом%%' OR
                          lower(title) LIKE '%%запчаст%%' OR lower(title) LIKE '%%ремонт%%' OR
                          lower(title) LIKE '%%не работ%%' OR lower(title) LIKE '%%не включ%%' OR
                          lower(title) LIKE '%%дефект%%'  OR lower(title) LIKE '%%трещин%%' OR
                          lower(title) LIKE '%%поломк%%'  OR lower(title) LIKE '%%без дисплея%%' OR
                          lower(title) LIKE '%%без аккумулятора%%' OR
                          lower(title) LIKE '%%broken%%'  OR lower(title) LIKE '%%damaged%%' OR
                          lower(title) LIKE '%%for parts%%' OR lower(title) LIKE '%%repair%%' OR
                          lower(title) LIKE '%%defect%%'  OR
                          lower(title) LIKE '%%buzilgan%%' OR lower(title) LIKE '%%singan%%' OR
                          lower(title) LIKE '%%nosoz%%'   OR lower(title) LIKE '%%ehtiyot qism%%'
                        ) AS is_damaged
                    FROM marketplace.electronics
                    WHERE category = %s
                      AND model IS NOT NULL AND model != '' AND price > 0
                      AND (%s = 0 OR scraped_at >= NOW() - INTERVAL '1 day' * %s)
                ),
                filtered AS (
                    SELECT model, price_usd, is_damaged FROM base
                    WHERE price_usd BETWEEN %s AND %s
                )
                SELECT model,
                    is_damaged,
                    COUNT(*)                                                       AS cnt,
                    ROUND(MIN(price_usd))                                          AS raw_min,
                    ROUND(MAX(price_usd))                                          AS raw_max,
                    ROUND(PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY price_usd)) AS min_usd,
                    ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY price_usd)) AS max_usd,
                    ROUND(AVG(price_usd))                                          AS avg_usd
                FROM filtered
                GROUP BY model, is_damaged
                HAVING COUNT(*) >= %s
                ORDER BY AVG(price_usd)
            """, [category, category, category, category, category, uzs_rate, category,
                  days, days, min_usd, max_usd, min_count])
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]

        # Split normal vs damaged, normalise + merge duplicates, drop generic buckets
        merged: dict[str, dict] = {}
        damaged: dict[str, dict] = {}
        for r in rows:
            if r['model'] in skip:
                continue
            key = normalize(r['model'])
            if r['is_damaged']:
                # damaged listings: report raw min/max (full spread), not percentiles
                d = damaged.setdefault(key, {'model': key, 'cnt': 0,
                                             'min_usd': r['raw_min'],
                                             'max_usd': r['raw_max']})
                d['cnt']     += r['cnt']
                d['min_usd']  = min(d['min_usd'], r['raw_min'])
                d['max_usd']  = max(d['max_usd'], r['raw_max'])
                continue
            if key not in merged:
                merged[key] = {'model': key, 'cnt': 0,
                               'min_usd': r['min_usd'], 'max_usd': r['max_usd'],
                               'avg_usd': r['avg_usd']}
            m = merged[key]
            m['cnt']     += r['cnt']
            m['min_usd']  = min(m['min_usd'], r['min_usd'])
            m['max_usd']  = max(m['max_usd'], r['max_usd'])
            # recalculate avg as weighted average
            total_old = m['cnt'] - r['cnt']
            m['avg_usd'] = round(
                (m['avg_usd'] * total_old + r['avg_usd'] * r['cnt']) / m['cnt']
            ) if m['cnt'] else r['avg_usd']

        result          = sorted(merged.values(),  key=lambda x: x['avg_usd'])
        damaged_result  = sorted(damaged.values(), key=lambda x: x['min_usd'])

        # Individual broken / for-parts listings (no count threshold) so they can
        # be surfaced separately instead of disappearing into the aggregate. Uses
        # the SAME damage keyword set as the base CTE above, so every listing that
        # is excluded from the main report shows up here with its title and price.
        with connection.cursor() as cur:
            cur.execute("""
                WITH with_chip AS (
                    SELECT
                        CASE
                          WHEN %s = 'macbook'
                               AND model IN ('MacBook Air', 'MacBook Pro')
                               AND specs IS NOT NULL
                               AND specs->>'chip' IS NOT NULL
                               AND specs->>'chip' != ''
                          THEN model || ' ' || (specs->>'chip')
                          WHEN %s = 'macbook'
                               AND model IN ('MacBook Air', 'MacBook Pro')
                               AND title ~* '\\mM[1-9]\\M'
                          THEN model || ' '
                               || upper(substring(title from '(?i)\\mM[1-9]\\M'))
                               || COALESCE(
                                    ' ' || initcap((regexp_match(
                                        title, '(?i)M[1-9]\\s*(pro|max)'))[1]),
                                    '')
                          WHEN %s = 'macbook'
                               AND model IN ('MacBook Air', 'MacBook Pro')
                          THEN model || ' (Intel)'
                          ELSE model
                        END AS model,
                        title,
                        CASE WHEN price_currency = 'USD' THEN price::numeric
                             ELSE price::numeric / %s END AS price_usd
                    FROM marketplace.electronics
                    WHERE category = %s
                      AND model IS NOT NULL AND model != '' AND price > 0
                      AND (%s = 0 OR scraped_at >= NOW() - INTERVAL '1 day' * %s)
                      AND (
                        lower(title) LIKE '%%разбит%%' OR lower(title) LIKE '%%слом%%' OR
                        lower(title) LIKE '%%запчаст%%' OR lower(title) LIKE '%%ремонт%%' OR
                        lower(title) LIKE '%%не работ%%' OR lower(title) LIKE '%%не включ%%' OR
                        lower(title) LIKE '%%дефект%%'  OR lower(title) LIKE '%%трещин%%' OR
                        lower(title) LIKE '%%поломк%%'  OR lower(title) LIKE '%%без дисплея%%' OR
                        lower(title) LIKE '%%без аккумулятора%%' OR
                        lower(title) LIKE '%%broken%%'  OR lower(title) LIKE '%%damaged%%' OR
                        lower(title) LIKE '%%for parts%%' OR lower(title) LIKE '%%repair%%' OR
                        lower(title) LIKE '%%defect%%'  OR
                        lower(title) LIKE '%%buzilgan%%' OR lower(title) LIKE '%%singan%%' OR
                        lower(title) LIKE '%%nosoz%%'   OR lower(title) LIKE '%%ehtiyot qism%%'
                      )
                )
                SELECT model, title, ROUND(price_usd) AS price_usd
                FROM with_chip
                ORDER BY price_usd
            """, [category, category, category, uzs_rate, category, days, days])
            broken_rows = cur.fetchall()

        broken_listings = [
            {'model': normalize(r[0]), 'title': r[1], 'price_usd': int(r[2] or 0)}
            for r in broken_rows
        ]

        return Response({'category': category,
                         'models': result,
                         'damaged_models': damaged_result,
                         'broken_listings': broken_listings})


class ElectronicsListings(APIView):
    """
    GET /api/electronics/listings/?category=macbook&model_label=MacBook+Air+M1&days=7&page=0

    Returns paginated individual listings (title, price, source url) for one
    display model, using the SAME chip-resolution + normalization + price-band +
    damage filtering as ElectronicsReport, so the listing set matches the count
    shown in the report.
    """
    PAGE_SIZE = 5

    def get(self, request):
        category    = request.query_params.get('category', 'iphone')
        model_label = (request.query_params.get('model_label') or '').strip()
        max_usd     = ElectronicsReport.MAX_USD.get(category, 4000)
        min_usd     = ElectronicsReport.MIN_USD.get(category, 50)
        uzs_rate    = _get_uzs_rate()
        skip        = _SKIP_MODELS.get(category, set())
        normalize   = _NORMALIZERS.get(category, lambda x: x.strip())

        try:
            days = int(request.query_params.get('days', 0))
        except (TypeError, ValueError):
            days = 0
        if days < 0:
            days = 0
        try:
            page = int(request.query_params.get('page', 0))
        except (TypeError, ValueError):
            page = 0
        if page < 0:
            page = 0

        if not model_label:
            return Response({'total': 0, 'page': 0, 'pages': 0, 'listings': []})

        with connection.cursor() as cur:
            cur.execute("""
                WITH base AS (
                    SELECT
                        CASE
                          WHEN %s = 'macbook'
                               AND model IN ('MacBook Air', 'MacBook Pro')
                               AND specs IS NOT NULL
                               AND specs->>'chip' IS NOT NULL
                               AND specs->>'chip' != ''
                          THEN model || ' ' || (specs->>'chip')
                          WHEN %s = 'macbook'
                               AND model IN ('MacBook Air', 'MacBook Pro')
                               AND title ~* '\\mM[1-9]\\M'
                          THEN model || ' '
                               || upper(substring(title from '(?i)\\mM[1-9]\\M'))
                               || COALESCE(
                                    ' ' || initcap((regexp_match(
                                        title, '(?i)M[1-9]\\s*(pro|max)'))[1]),
                                    '')
                          WHEN %s = 'macbook'
                               AND model IN ('MacBook Air', 'MacBook Pro')
                          THEN model || ' (Intel)'
                          -- CPU: resolve bare 'Intel Core'/'AMD Ryzen' labels — must
                          -- match ElectronicsReport exactly (model_id, then title).
                          WHEN %s = 'cpu'
                               AND model IN ('Intel Core', 'AMD Ryzen', 'Intel Xeon', 'AMD')
                          THEN CASE
                                 WHEN specs IS NOT NULL
                                      AND COALESCE(specs->>'model_id', '') != ''
                                   THEN model || ' ' || (specs->>'model_id')
                                 WHEN title ~* '\\multra\\s+[3579]\\s*[0-9]{3}'
                                   THEN 'Intel Core Ultra '
                                        || (regexp_match(title, '(?i)ultra\\s+([3579])\\s*([0-9]{3}[a-z]*)'))[1]
                                        || ' '
                                        || upper((regexp_match(title, '(?i)ultra\\s+([3579])\\s*([0-9]{3}[a-z]*)'))[2])
                                 WHEN title ~* '\\mxeon\\M'
                                   THEN 'Intel Xeon'
                                 WHEN title ~* '\\mi[3579][\\s-]?[0-9]{4}'
                                   THEN 'Intel Core i'
                                        || (regexp_match(title, '(?i)\\mi([3579])[\\s-]?([0-9]{4,5}[a-z]*)'))[1]
                                        || '-'
                                        || upper((regexp_match(title, '(?i)\\mi([3579])[\\s-]?([0-9]{4,5}[a-z]*)'))[2])
                                 ELSE model
                               END
                          ELSE model
                        END AS model,
                        title,
                        url,
                        scraped_at,
                        CASE WHEN price_currency = 'USD' THEN price::numeric
                             ELSE price::numeric / %s END AS price_usd,
                        (
                          lower(title) LIKE '%%разбит%%' OR lower(title) LIKE '%%слом%%' OR
                          lower(title) LIKE '%%запчаст%%' OR lower(title) LIKE '%%ремонт%%' OR
                          lower(title) LIKE '%%не работ%%' OR lower(title) LIKE '%%не включ%%' OR
                          lower(title) LIKE '%%дефект%%'  OR lower(title) LIKE '%%трещин%%' OR
                          lower(title) LIKE '%%поломк%%'  OR lower(title) LIKE '%%без дисплея%%' OR
                          lower(title) LIKE '%%без аккумулятора%%' OR
                          lower(title) LIKE '%%broken%%'  OR lower(title) LIKE '%%damaged%%' OR
                          lower(title) LIKE '%%for parts%%' OR lower(title) LIKE '%%repair%%' OR
                          lower(title) LIKE '%%defect%%'  OR
                          lower(title) LIKE '%%buzilgan%%' OR lower(title) LIKE '%%singan%%' OR
                          lower(title) LIKE '%%nosoz%%'   OR lower(title) LIKE '%%ehtiyot qism%%'
                        ) AS is_damaged
                    FROM marketplace.electronics
                    WHERE category = %s
                      AND model IS NOT NULL AND model != '' AND price > 0
                      AND (%s = 0 OR scraped_at >= NOW() - INTERVAL '1 day' * %s)
                )
                SELECT model, title, url, scraped_at, ROUND(price_usd) AS price_usd
                FROM base
                WHERE NOT is_damaged
                  AND price_usd BETWEEN %s AND %s
                ORDER BY price_usd
            """, [category, category, category, category, uzs_rate, category,
                  days, days, min_usd, max_usd])
            rows = cur.fetchall()

        # Normalize + match to the requested display model (done in Python to
        # mirror ElectronicsReport's normalization exactly).
        matched = []
        for raw_model, title, url, scraped_at, price_usd in rows:
            if raw_model in skip:
                continue
            if normalize(raw_model) != model_label:
                continue
            matched.append({
                'title': title or '',
                'price_usd': int(price_usd or 0),
                'source_url': url or '',
                'scraped_at': scraped_at.isoformat() if scraped_at else None,
            })

        total = len(matched)
        pages = (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE if total else 0
        if pages and page >= pages:
            page = pages - 1
        start = page * self.PAGE_SIZE
        listings = matched[start:start + self.PAGE_SIZE]

        return Response({
            'total': total,
            'page': page,
            'pages': pages,
            'listings': listings,
        })
