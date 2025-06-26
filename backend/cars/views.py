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
            .annotate(count=Count('fuel_type'))
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
                .annotate(count=Count(field))
                .order_by('-count')
            )
            result[field] = {
                entry[field] or 'None': entry['count']
                for entry in summary
            }
        return Response(result)


class CarFilteredList(APIView):
    def get(self, request):
        filters = {}
        allowed = ['fuel_type', 'gear_type', 'color', 'vehicle_type', 'condition', 'brand', 'model', 'year']
        for key in allowed:
            value = request.query_params.get(key)
            if value:
                filters[key] = value

        queryset = Car.objects.filter(**filters)
        serializer = CarShortSerializer(queryset, many=True)
        return Response(serializer.data)