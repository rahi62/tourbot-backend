from rest_framework import serializers
from .models import Tour, TourPackage


class TourSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tour
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TourPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourPackage
        fields = '__all__'
        read_only_fields = ()

