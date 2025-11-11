from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Min, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    TopAgencySerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['username'] = user.username
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'user': UserSerializer(user).data,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    Get current user profile.
    """
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update current user profile.
    """
    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Get current user information including role.
    Alias for profile endpoint with more RESTful naming.
    """
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def top_agencies(request):
    """Return a curated list of top-performing agencies with metrics."""
    try:
        limit = int(request.query_params.get('limit', 12))
    except (TypeError, ValueError):
        limit = 12
    limit = max(3, min(limit, 24))

    today = timezone.now().date()

    queryset = (
        User.objects.filter(role='agency')
        .annotate(
            total_tours=Count('tour_packages', distinct=True),
            active_tour_count=Count(
                'tour_packages',
                filter=Q(tour_packages__is_active=True),
                distinct=True,
            ),
            featured_tour_count=Count(
                'tour_packages',
                filter=Q(tour_packages__is_active=True, tour_packages__is_featured=True),
                distinct=True,
            ),
            discounted_tour_count=Count(
                'tour_packages',
                filter=Q(tour_packages__is_active=True, tour_packages__is_discounted=True),
                distinct=True,
            ),
            destinations_count=Count(
                'tour_packages__destination_country',
                filter=Q(tour_packages__is_active=True),
                distinct=True,
            ),
            average_price=Avg(
                'tour_packages__price',
                filter=Q(tour_packages__is_active=True),
            ),
            next_departure=Min(
                'tour_packages__start_date',
                filter=Q(tour_packages__is_active=True, tour_packages__start_date__gte=today),
            ),
        )
        .prefetch_related(
            'tour_packages'
        )
        .order_by(
            '-is_featured_agency',
            'featured_priority',
            '-active_tour_count',
            '-featured_tour_count',
            '-total_tours',
            'company_name',
        )
    )

    agencies = list(queryset[:limit])
    serializer = TopAgencySerializer(agencies, many=True, context={'request': request})
    return Response(serializer.data)

