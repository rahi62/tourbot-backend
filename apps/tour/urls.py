from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TourPackage

router = DefaultRouter()
router.register(r'tours', TourPackage, basename='tour')

urlpatterns = [
    path('', include(router.urls)),
]

