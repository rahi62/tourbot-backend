from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone_number',
            'company_name',
            'agency_tagline',
            'is_featured_agency',
            'featured_priority',
        )
        read_only_fields = ('id',)


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm Password')

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'password',
            'password2',
            'first_name',
            'last_name',
            'role',
            'phone_number',
            'company_name',
            'agency_tagline',
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        # Set default role to 'traveler' if not specified
        if 'role' not in validated_data or not validated_data.get('role'):
            validated_data['role'] = 'traveler'
        # Only allow setting role to 'traveler' during registration
        # Admins and agencies should be created via admin panel
        if validated_data.get('role') not in ['traveler']:
            validated_data['role'] = 'traveler'
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone_number',
            'company_name',
            'agency_tagline',
            'is_featured_agency',
            'featured_priority',
            'date_joined',
        )
        read_only_fields = (
            'id',
            'username',
            'date_joined',
            'role',
            'is_featured_agency',
            'featured_priority',
        )


class TopAgencySerializer(serializers.ModelSerializer):
    active_tour_count = serializers.IntegerField(default=0)
    featured_tour_count = serializers.IntegerField(default=0)
    discounted_tour_count = serializers.IntegerField(default=0)
    destinations_count = serializers.IntegerField(default=0)
    average_price = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    next_departure = serializers.DateField(allow_null=True)
    highlight_destinations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'company_name',
            'first_name',
            'last_name',
            'agency_tagline',
            'is_featured_agency',
            'featured_priority',
            'active_tour_count',
            'featured_tour_count',
            'discounted_tour_count',
            'destinations_count',
            'average_price',
            'next_departure',
            'highlight_destinations',
        )

    def get_highlight_destinations(self, obj):
        active_destinations = (
            obj.tour_packages.filter(is_active=True)
            .values_list('destination_country', flat=True)
            .distinct()
        )
        return list(active_destinations[:3])

