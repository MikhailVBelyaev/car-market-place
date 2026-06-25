from rest_framework import serializers
from .models import Car, Apartment, Electronics

class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = '__all__'  # Include all fields


class ApartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Apartment
        fields = '__all__'


class ElectronicsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Electronics
        fields = '__all__'
