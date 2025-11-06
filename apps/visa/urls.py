from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VisaRequest

router = DefaultRouter()
router.register(r'visas', VisaRequest, basename='visa')

urlpatterns = [
    path('', include(router.urls)),
]

