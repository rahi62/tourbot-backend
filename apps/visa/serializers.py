from rest_framework import serializers
from .models import Visa, VisaRequest


class VisaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visa
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class VisaRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaRequest
        fields = '__all__'
        read_only_fields = ('submitted_at', 'status', 'user')

