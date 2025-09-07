from django.db.models import Count, Q
from rest_framework import serializers
from django.db.models.functions import TruncDate
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
