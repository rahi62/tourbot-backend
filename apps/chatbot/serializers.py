from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models import (
    ChatInteraction,
    ChatLead,
    ChatMessage,
    Interaction,
    Offer,
    Referral,
    UserPreference,
    VisaKnowledge,
)
from apps.tour.constants import TRAVEL_STYLE_CHOICES


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'
        read_only_fields = ('user', 'created_at')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('message',)


class ChatLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatLead
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'user')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class ChatInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatInteraction
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'user')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class ReferralSerializer(serializers.ModelSerializer):
    offer = serializers.PrimaryKeyRelatedField(queryset=Offer.objects.filter(is_active=True))

    class Meta:
        model = Referral
        fields = (
            'id',
            'code',
            'offer',
            'created_by',
            'metadata',
            'created_at',
            'expires_at',
        )
        read_only_fields = ('id', 'code', 'created_by', 'created_at')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class ReferralCreateSerializer(serializers.Serializer):
    offer_id = serializers.PrimaryKeyRelatedField(queryset=Offer.objects.filter(is_active=True), source='offer')
    metadata = serializers.JSONField(required=False)
    expires_at = serializers.DateTimeField(required=False)
    session_id = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        validated_data.pop('session_id', None)
        return Referral.objects.create(**validated_data)


class InteractionSerializer(serializers.ModelSerializer):
    offer = serializers.PrimaryKeyRelatedField(queryset=Offer.objects.filter(is_active=True))
    referral = serializers.PrimaryKeyRelatedField(queryset=Referral.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Interaction
        fields = (
            'id',
            'event',
            'offer',
            'referral',
            'user',
            'session_id',
            'referral_code',
            'payload',
            'created_at',
        )
        read_only_fields = ('id', 'user', 'created_at')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        # If referral_code provided but referral null attempt auto-match
        referral_code = validated_data.get('referral_code')
        if referral_code and not validated_data.get('referral'):
            try:
                validated_data['referral'] = Referral.objects.get(code=referral_code)
            except Referral.DoesNotExist:
                pass
        return super().create(validated_data)


class PaymentCreateSerializer(serializers.Serializer):
    offer_id = serializers.PrimaryKeyRelatedField(queryset=Offer.objects.filter(is_active=True), source='offer')
    referral_code = serializers.CharField(required=False, allow_blank=True)
    session_id = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        referral_code = attrs.get('referral_code')
        if referral_code:
            try:
                referral = Referral.objects.get(code=referral_code)
                attrs['referral'] = referral
            except Referral.DoesNotExist:
                raise serializers.ValidationError({'referral_code': 'Referral code not found'})
        return attrs


class PaymentWebhookSerializer(serializers.Serializer):
    referral_code = serializers.CharField()
    status = serializers.ChoiceField(choices=['success', 'failed'])
    payload = serializers.JSONField(required=False)

    def validate(self, attrs):
        referral_code = attrs['referral_code']
        try:
            attrs['referral'] = Referral.objects.get(code=referral_code)
        except Referral.DoesNotExist:
            raise serializers.ValidationError({'referral_code': 'Referral not found'})
        return attrs


class UserPreferenceSerializer(serializers.ModelSerializer):
    favorite_destinations = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = UserPreference
        fields = (
            'id',
            'user',
            'phone',
            'favorite_destinations',
            'travel_style',
            'budget_min',
            'budget_max',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'user')

    def validate_favorite_destinations(self, value):
        cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        return cleaned

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data.setdefault('user', request.user)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        favorite = validated_data.get('favorite_destinations')
        if favorite is not None and not favorite:
            # ensure we store empty list rather than None
            validated_data['favorite_destinations'] = []
        return super().update(instance, validated_data)


class VisaKnowledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaKnowledge
        fields = (
            'id',
            'country',
            'visa_type',
            'summary',
            'requirements',
            'processing_time',
            'notes',
            'source_url',
            'is_active',
            'last_updated',
        )
        read_only_fields = ('id', 'last_updated')


class TourSuggestionRequestSerializer(serializers.Serializer):
    session_id = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    favorite_destinations = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    destination = serializers.CharField(required=False, allow_blank=True)
    travel_style = serializers.ChoiceField(
        choices=[choice[0] for choice in TRAVEL_STYLE_CHOICES],
        required=False,
        allow_blank=True,
    )
    budget_min = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    budget_max = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)
    metadata = serializers.JSONField(required=False)

    def validate_favorite_destinations(self, value):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    def validate_travel_style(self, value):
        if value in (None, '', 'general'):
            return 'general'
        return value

    def validate(self, attrs):
        budget_min = attrs.get('budget_min')
        budget_max = attrs.get('budget_max')
        if budget_min is not None and budget_max is not None:
            try:
                if Decimal(budget_min) > Decimal(budget_max):
                    raise serializers.ValidationError({'budget_max': 'Must be greater than or equal to budget_min'})
            except (InvalidOperation, TypeError):
                raise serializers.ValidationError({'budget_min': 'Invalid budget value'})
        return attrs


