from django.db.models import Avg, Count, Min, Max, Q
from django.db import connection
from rest_framework import serializers
from django.db.models.functions import TruncDate, TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Car
from .serializers import CarSerializer
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils import timezone

# Set up logging
logger = logging.getLogger(__name__)

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

        base_qs = Car.objects.filter(
            brand=brand, model=model_name, year=year,
            gear_type=gear_type, color=color, price__gt=0,
        )

        # Search order: tighter band first, widen only if needed
        search_plans = [
            (30, 0.25),   # last 30 days, ±25%
            (60, 0.25),   # last 60 days, ±25%
            (30, 0.50),   # last 30 days, ±50%
            (90, 0.50),   # last 90 days, ±50%
        ]

        for days, band in search_plans:
            low  = int(mileage * (1 - band))
            high = int(mileage * (1 + band))
            qs = base_qs.filter(
                mileage__gte=low, mileage__lte=high,
                created_at__gte=timezone.now() - timedelta(days=days),
            )
            count = qs.count()
            if count >= self.MIN_LISTINGS:
                prices = sorted(qs.values_list('price', flat=True))
                median = prices[len(prices) // 2]
                return Response({
                    "price":        round(median),
                    "avg":          round(sum(prices) / len(prices)),
                    "min":          round(prices[0]),
                    "max":          round(prices[-1]),
                    "source":       f"market_{days}d",
                    "count":        count,
                    "period":       f"last {days} days",
                    "mileage_band": f"{low:,}–{high:,} km",
                    "mileage_low":  low,
                    "mileage_high": high,
                })

        # No plan found enough data — ML fallback triggered by caller
        low  = int(mileage * 0.75)
        high = int(mileage * 1.25)
        return Response({
            "price":        None,
            "source":       "insufficient_data",
            "count":        base_qs.filter(
                mileage__gte=low, mileage__lte=high,
                created_at__gte=timezone.now() - timedelta(days=90),
            ).count(),
            "mileage_low":  low,
            "mileage_high": high,
        })


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
    def get(self, request):
        top_brands = ['Chevrolet', 'BYD', 'Hyundai']
        result = []
        for brand in top_brands:
            years_qs = (
                Car.objects.filter(brand=brand, price__gt=0, year__gte=2010, year__lte=2025)
                .values('year')
                .annotate(count=Count('car_id'), avg_price=Avg('price'))
                .filter(count__gte=5)
                .order_by('year')
            )
            result.append({'brand': brand, 'years': [
                {'year': r['year'], 'count': r['count'], 'avg_price': round(float(r['avg_price']))}
                for r in years_qs
            ]})
        return Response({'brands': result})


class BestValue(APIView):
    def get(self, request):
        since = timezone.now() - timedelta(days=7)
        with connection.cursor() as cur:
            cur.execute("""
                WITH model_stats AS (
                    SELECT brand, model, year,
                           PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price) AS p25,
                           AVG(price) AS avg_price, COUNT(*) AS cnt
                    FROM marketplace.cars
                    WHERE created_at >= %s AND price > 0
                    GROUP BY brand, model, year HAVING COUNT(*) >= 5
                )
                SELECT c.brand, c.model, c.year, c.price::int, c.mileage,
                       ms.avg_price::int, ms.p25::int,
                       ROUND((ms.avg_price - c.price) / ms.avg_price * 100, 1) AS discount_pct
                FROM marketplace.cars c
                JOIN model_stats ms USING (brand, model, year)
                WHERE c.created_at >= %s AND c.price > 0 AND c.price <= ms.p25
                ORDER BY discount_pct DESC LIMIT 10
            """, [since, since])
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return Response({'listings': rows, 'period_days': 7})


class SeasonalTrends(APIView):
    def get(self, request):
        top_brands = ['Chevrolet', 'BYD', 'Hyundai']
        result = []
        for brand in top_brands:
            months_qs = (
                Car.objects.filter(brand=brand, price__gt=0)
                .annotate(month=TruncMonth('created_at'))
                .values('month')
                .annotate(avg_price=Avg('price'), count=Count('car_id'))
                .filter(count__gte=5)
                .order_by('month')
            )
            result.append({'brand': brand, 'months': [
                {'month': r['month'].strftime('%Y-%m'),
                 'avg_price': round(float(r['avg_price'])), 'count': r['count']}
                for r in months_qs
            ]})
        return Response({'brands': result})


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
