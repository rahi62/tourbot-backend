from rest_framework import serializers
from .models import Tour, TourPackage


class TourSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tour
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TourPackageSerializer(serializers.ModelSerializer):
    agency_name = serializers.SerializerMethodField()
    agency_company = serializers.SerializerMethodField()

    class Meta:
        model = TourPackage
        fields = '__all__'
        read_only_fields = ()

    def get_agency_name(self, obj):
        if obj.user:
            full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
            if full_name:
                return full_name
            return obj.user.username
        return None

    def get_agency_company(self, obj):
        if obj.user and hasattr(obj.user, 'company_name') and obj.user.company_name:
            return obj.user.company_name
        return None

