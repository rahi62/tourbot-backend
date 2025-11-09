from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.db import models
from .models import Tour, TourPackage
from .serializers import TourSerializer, TourPackageSerializer
from .permissions import IsAuthenticatedForWrite, IsAgencyOrAdminForWrite


class TourViewSet(viewsets.ModelViewSet):
    """
    ViewSet for the Tour model (legacy model).
    """
    queryset = Tour.objects.all()
    serializer_class = TourSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Tour.objects.all()
        if self.request.query_params.get('active_only') == 'true':
            queryset = queryset.filter(is_active=True)
        # If user is agency, show only their tours; admin can see all
        if self.request.user.is_authenticated and self.request.user.is_agency():
            queryset = queryset.filter(user=self.request.user)
        return queryset
    
    def perform_create(self, serializer):
        # Only authenticated users (agencies/admins) can create tours
        serializer.save(user=self.request.user)


class TourPackageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for the TourPackage model with full CRUD operations.
    - All users (including unauthenticated) can read (GET, LIST)
    - Only users with role 'agency' or 'admin' can create, update, or delete
    """
    queryset = TourPackage.objects.all()
    serializer_class = TourPackageSerializer
    permission_classes = [IsAgencyOrAdminForWrite]

    def get_queryset(self):
        queryset = TourPackage.objects.all()
        
        # Filter by active status if requested
        if self.request.query_params.get('active_only') == 'true':
            queryset = queryset.filter(is_active=True)
        
        # Search filter - search in title, description, and destination_country
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search) |
                models.Q(description__icontains=search) |
                models.Q(destination_country__icontains=search)
            )
        
        # Filter by destination country if requested
        destination = self.request.query_params.get('destination_country')
        if destination:
            queryset = queryset.filter(destination_country__icontains=destination)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price')
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass  # Ignore invalid min_price
        
        max_price = self.request.query_params.get('max_price')
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass  # Ignore invalid max_price
        
        # Filter by travel date (start_date >= date)
        date = self.request.query_params.get('date')
        if date:
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                queryset = queryset.filter(start_date__gte=date_obj)
            except (ValueError, TypeError):
                pass  # Ignore invalid date format

        # Filter by featured or discounted flags
        featured = self.request.query_params.get('is_featured')
        if featured is not None:
            queryset = queryset.filter(is_featured=featured.lower() in ('true', '1'))

        discounted = self.request.query_params.get('is_discounted')
        if discounted is not None:
            queryset = queryset.filter(is_discounted=discounted.lower() in ('true', '1'))

        return queryset
    
    def perform_create(self, serializer):
        # Only agency or admin users can create tours
        serializer.save()
    
    def perform_update(self, serializer):
        # Only agency or admin users can update tours
        serializer.save()
    
    def perform_destroy(self, instance):
        # Only agency or admin users can delete tours
        instance.delete()

