from django.db.models import Count
from rest_framework import serializers
from django.db.models.functions import TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Car
from .serializers import CarSerializer
from django.db.models import Count

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

        # Format 'None' for null values
        result = {
            entry['fuel_type'] or 'None': entry['count']
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
                entry[field] or 'None': entry['count']
                for entry in summary
            }
        return Response(result)

class CarFilteredList(APIView):
    """
    Returns a filtered list of cars, with dynamic allowed filters based on /api/cars/filters-summary/.
    Also provides filter configuration for client UI.
    """
    def get(self, request):
        # Get filter summary to determine allowed and available filters dynamically
        summary_view = CarFiltersSummary()
        summary_response = summary_view.get(request)
        summary_data = summary_response.data if hasattr(summary_response, 'data') else summary_response

        # Exclude filters with only one value (e.g., only "None" for vehicle_type)
        allowed = []
        for key, value_counts in summary_data.items():
            # If only one value across dataset, skip this filter
            if len(value_counts) <= 1:
                continue
            allowed.append(key)

        # Build filters from request
        filters = {}
        for key in allowed:
            value = request.query_params.get(key)
            if value:
                filters[key] = value

        queryset = Car.objects.filter(**filters)
        serializer = CarShortSerializer(queryset, many=True)

        # Build filter config for client
        filter_config = {}
        for key in allowed:
            values = summary_data.get(key, {})
            # Compose config per requirements
            if key == "fuel_type":
                # Checkbox with: Gasoline, Electric, Diesel, None (+ counts)
                opts = []
                for v in ['Gasoline', 'Electric', 'Diesel', 'None']:
                    opts.append({
                        "value": v,
                        "label": v,
                        "count": values.get(v, 0)
                    })
                filter_config[key] = {
                    "type": "checkbox",
                    "options": opts
                }
            elif key == "gear_type":
                # Checkbox: AT, MT, None
                opts = []
                for v in ['AT', 'MT', 'None']:
                    opts.append({
                        "value": v,
                        "label": v,
                        "count": values.get(v, 0)
                    })
                filter_config[key] = {
                    "type": "checkbox",
                    "options": opts
                }
            elif key == "color":
                # Dropdown with available colors
                opts = []
                for v, cnt in values.items():
                    opts.append({
                        "value": v,
                        "label": v,
                        "count": cnt
                    })
                filter_config[key] = {
                    "type": "dropdown",
                    "options": opts
                }
            elif key == "brand":
                # Dropdown (not checkbox)
                opts = []
                for v, cnt in values.items():
                    opts.append({
                        "value": v,
                        "label": v,
                        "count": cnt
                    })
                filter_config[key] = {
                    "type": "dropdown",
                    "options": opts
                }
            elif key == "model":
                opts = []
                for v, cnt in values.items():
                    opts.append({
                        "value": v,
                        "label": v,
                        "count": cnt
                    })
                filter_config[key] = {
                    "type": "dropdown",
                    "options": opts
                }
            elif key == "year":
                # Group years as described
                years = []
                for v in values.keys():
                    try:
                        y = int(v)
                        years.append(y)
                    except Exception:
                        continue
                years = sorted(years)
                opts = []
                # Individual years: 2015–2025
                for y in range(2015, 2026):
                    if str(y) in values:
                        opts.append({
                            "value": str(y),
                            "label": str(y),
                            "count": values[str(y)]
                        })
                # Group 2010–2014
                group_2010_2014 = sum([values.get(str(y), 0) for y in range(2010, 2015)])
                if group_2010_2014:
                    opts.append({
                        "value": "2010-2014",
                        "label": "2010–2014",
                        "count": group_2010_2014
                    })
                # Group 2000–2009
                group_2000_2009 = sum([values.get(str(y), 0) for y in range(2000, 2010)])
                if group_2000_2009:
                    opts.append({
                        "value": "2000-2009",
                        "label": "2000–2009",
                        "count": group_2000_2009
                    })
                # Group 1990–1999
                group_1990_1999 = sum([values.get(str(y), 0) for y in range(1990, 2000)])
                if group_1990_1999:
                    opts.append({
                        "value": "1990-1999",
                        "label": "1990–1999",
                        "count": group_1990_1999
                    })
                # Group older
                group_older = sum([values.get(str(y), 0) for y in years if y < 1990])
                if group_older:
                    opts.append({
                        "value": "before-1990",
                        "label": "Before 1990",
                        "count": group_older
                    })
                filter_config[key] = {
                    "type": "dropdown",
                    "options": opts
                }
            else:
                # Default: dropdown with available values
                opts = []
                for v, cnt in values.items():
                    opts.append({
                        "value": v,
                        "label": v,
                        "count": cnt
                    })
                filter_config[key] = {
                    "type": "dropdown",
                    "options": opts
                }

        return Response({
            "results": serializer.data,
            "filters": filter_config,
        })