from django.db.models import Count, Q
from rest_framework import serializers
from django.db.models.functions import TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Car
from .serializers import CarSerializer
import logging

# Set up logging
logger = logging.getLogger(__name__)

class CarShortSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = ['description', 'price', 'location', 'created_at', 'year', 'mileage']

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
        fields = ['fuel_type', 'gear_type', 'color', 'vehicle_type', 'condition', 'brand', 'model', 'year']
        result = {}
        for field in fields:
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

class CarFilteredList(APIView):
    """
    Returns a filtered list of cars, with dynamic allowed filters based on /api/cars/filters-summary/.
    Also provides filter configuration for client UI.
    """
    def get(self, request):
        # Get filter summary
        summary_view = CarFiltersSummary()
        summary_response = summary_view.get(request)
        summary_data = summary_response.data if hasattr(summary_response, 'data') else summary_response
        logger.debug(f"Summary data: {summary_data}")

        # Define allowed filters, including price and mileage
        allowed = []
        for key, value_counts in summary_data.items():
            if len(value_counts) > 1 or key == 'year':  # Include year even if single value
                allowed.append(key)
        allowed.extend(['price', 'mileage'])

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
                elif key == 'year':
                    try:
                        filters['year'] = int(value)
                    except ValueError:
                        logger.error(f"Invalid year value: {value}")
                        continue
                elif value == 'None' and key in ['fuel_type', 'gear_type']:
                    filters[f'{key}__isnull'] = True
                else:
                    filters[key] = value

        queryset = Car.objects.filter(**filters)
        serializer = CarShortSerializer(queryset, many=True)

        # Build filter config for client
        filter_config = {}
        for key in allowed:
            values = summary_data.get(key, {})
            if key == "fuel_type":
                opts = [
                    {"value": "Gasoline", "label": "Gasoline", "count": values.get("Gasoline", 0)},
                    {"value": "Electric", "label": "Electric", "count": values.get("Electric", 0)},
                    {"value": "Diesel", "label": "Diesel", "count": values.get("Diesel", 0)},
                    {"value": "Hybrid", "label": "Hybrid", "count": values.get("Hybrid", 0)},
                    {"value": "Gas", "label": "Gas", "count": values.get("Gas", 0)},
                    {"value": "None", "label": "None", "count": values.get("None", 0)}
                ]
                filter_config[key] = {"type": "checkbox", "options": opts}
            elif key == "gear_type":
                opts = [
                    {"value": "AT", "label": "Automatic", "count": values.get("AT", 0)},
                    {"value": "MT", "label": "Manual", "count": values.get("MT", 0)},
                    {"value": "DSG", "label": "Dual-clutch", "count": values.get("DSG", 0)},
                    {"value": "None", "label": "None", "count": values.get("None", 0)}
                ]
                filter_config[key] = {"type": "checkbox", "options": opts}
            elif key == "year":
                years = []
                invalid_years = []
                for v in values.keys():
                    try:
                        y = int(v)
                        if 1900 <= y <= 2025:  # Restrict to reasonable years
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
                # Individual years: 2020–2025
                for y in range(2020, 2026):
                    opts.append({
                        "value": str(y),
                        "label": str(y),
                        "count": values.get(str(y), 0)
                    })
                # Group 2015–2019
                group_2015_2019 = sum([values.get(str(y), 0) for y in range(2015, 2020)])
                opts.append({
                    "value": "2015-2019",
                    "label": "2015–2019",
                    "count": group_2015_2019
                })
                # Group 2010–2014
                group_2010_2014 = sum([values.get(str(y), 0) for y in range(2010, 2015)])
                opts.append({
                    "value": "2010-2014",
                    "label": "2010–2014",
                    "count": group_2010_2014
                })
                # Group 2000–2009
                group_2000_2009 = sum([values.get(str(y), 0) for y in range(2000, 2010)])
                opts.append({
                    "value": "2000-2009",
                    "label": "2000–2009",
                    "count": group_2000_2009
                })
                # Group 1990–1999
                group_1990_1999 = sum([values.get(str(y), 0) for y in range(1990, 2000)])
                opts.append({
                    "value": "1990-1999",
                    "label": "1990–1999",
                    "count": group_1990_1999
                })
                # Group 1980–1989
                group_1980_1989 = sum([values.get(str(y), 0) for y in range(1980, 1990)])
                opts.append({
                    "value": "1980-1989",
                    "label": "1980–1989",
                    "count": group_1980_1989
                })
                # Group before 1980
                group_before_1980 = sum([values.get(str(y), 0) for y in years if y < 1980])
                opts.append({
                    "value": "before-1980",
                    "label": "Before 1980",
                    "count": group_before_1980
                })
                filter_config[key] = {"type": "dropdown", "options": opts}
            elif key == "price":
                opts = [
                    {"value": "0-5000", "label": "Under $5,000", "count": Car.objects.filter(price__lte=5000).count()},
                    {"value": "5000-10000", "label": "$5,000 - $10,000", "count": Car.objects.filter(price__range=(5000, 10000)).count()},
                    {"value": "10000-20000", "label": "$10,000 - $20,000", "count": Car.objects.filter(price__range=(10000, 20000)).count()},
                    {"value": "20000-50000", "label": "$20,000 - $50,000", "count": Car.objects.filter(price__range=(20000, 50000)).count()},
                    {"value": "50000-", "label": "Over $50,000", "count": Car.objects.filter(price__gt=50000).count()}
                ]
                filter_config[key] = {"type": "checkbox", "options": opts}
            elif key == "mileage":
                opts = [
                    {"value": "0-50000", "label": "Under 50,000 km", "count": Car.objects.filter(mileage__lte=50000).count()},
                    {"value": "50000-100000", "label": "50,000 - 100,000 km", "count": Car.objects.filter(mileage__range=(50000, 100000)).count()},
                    {"value": "100000-150000", "label": "100,000 - 150,000 km", "count": Car.objects.filter(mileage__range=(100000, 150000)).count()},
                    {"value": "150000-200000", "label": "150,000 - 200,000 km", "count": Car.objects.filter(mileage__range=(150000, 200000)).count()},
                    {"value": "200000-", "label": "Over 200,000 km", "count": Car.objects.filter(mileage__gt=200000).count()}
                ]
                filter_config[key] = {"type": "checkbox", "options": opts}
            else:
                opts = [
                    {"value": v, "label": v, "count": cnt}
                    for v, cnt in values.items()
                ]
                filter_config[key] = {"type": "dropdown", "options": opts}

        return Response({
            "results": serializer.data,
            "filters": filter_config,
        })