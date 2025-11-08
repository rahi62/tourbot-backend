from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from .models import Visa, VisaRequest
from .serializers import VisaSerializer, VisaRequestSerializer
from .permissions import VisaRequestPermission


class VisaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for the Visa model (legacy model).
    """
    queryset = Visa.objects.all()
    serializer_class = VisaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Visa.objects.all()
        # If user is agency, show only their visa requests; admin can see all
        if self.request.user.is_authenticated and self.request.user.is_agency():
            queryset = queryset.filter(user=self.request.user)
        return queryset
    
    def perform_create(self, serializer):
        # Only authenticated users can create visa requests
        serializer.save(user=self.request.user)


class VisaRequestViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    ViewSet for the VisaRequest model with create and list operations.
    - All users (including unauthenticated) can create (POST) visa requests
    - All users (including unauthenticated) can list (GET) visa requests
    - Only admins can view all visa requests
    - Travelers can see all requests (they can filter by their own data via full_name/passport_number)
    """
    queryset = VisaRequest.objects.all()
    serializer_class = VisaRequestSerializer
    permission_classes = [VisaRequestPermission]
    
    def get_queryset(self):
        queryset = VisaRequest.objects.all()
        
        # Handle authenticated users
        if self.request.user.is_authenticated:
            # Admins can see all visa requests
            if hasattr(self.request.user, 'is_admin') and self.request.user.is_admin():
                pass  # Return all requests
            # Agencies can see all visa requests (for managing)
            elif hasattr(self.request.user, 'is_agency') and self.request.user.is_agency():
                pass  # Return all requests
            # Travelers can only see their own visa requests
            elif hasattr(self.request.user, 'is_traveler') and self.request.user.is_traveler():
                queryset = queryset.filter(user=self.request.user)
        # Unauthenticated users can see all (but can't create authenticated requests)
        
        # Filter by status if requested
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by destination country if requested
        destination = self.request.query_params.get('destination_country')
        if destination:
            queryset = queryset.filter(destination_country__icontains=destination)
        
        # Filter by full_name if requested (for travelers to find their own requests)
        full_name = self.request.query_params.get('full_name')
        if full_name:
            queryset = queryset.filter(full_name__icontains=full_name)
        
        # Filter by passport_number if requested (for travelers to find their own requests)
        passport_number = self.request.query_params.get('passport_number')
        if passport_number:
            queryset = queryset.filter(passport_number__icontains=passport_number)
        
        return queryset
    
    def perform_create(self, serializer):
        """Associate the visa request with the user if authenticated."""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

