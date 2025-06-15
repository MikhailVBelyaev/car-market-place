from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Car
from .serializers import CarSerializer

class CarList(APIView):
    def get(self, request):
        cars = Car.objects.all()
        serializer = CarSerializer(cars, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CarSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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