"""
URL configuration for tourbot_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from apps.accounts.views import CustomTokenObtainPairView
from apps.tour.views import TourPackageViewSet
from apps.visa.views import VisaRequestViewSet

# Create a router and register viewsets
router = DefaultRouter()
router.register(r'tours', TourPackageViewSet, basename='tour-package')
router.register(r'visa-requests', VisaRequestViewSet, basename='visa-request')

urlpatterns = [
    path('admin/', admin.site.urls),
    # JWT Token endpoints
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # Authentication endpoints
    path('api/auth/', include('apps.accounts.urls')),
    # Chat endpoint
    path('api/chat/', include('apps.chatbot.urls')),
    # API routes
    path('api/', include(router.urls)),
]

# Serve media files
# In production, consider using cloud storage (AWS S3, Cloudinary, etc.)
# For Render, you can serve media files through Django, but it's not recommended for large files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # In production, serve media files through Django (not recommended for large files)
    # Consider using cloud storage for better performance
    from django.views.static import serve
    from django.urls import re_path
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

