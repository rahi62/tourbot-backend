"""
URL configuration for apps.
"""
from django.urls import path, include

urlpatterns = [
    path('visa/', include('apps.visa.urls')),
    path('tour/', include('apps.tour.urls')),
    path('chatbot/', include('apps.chatbot.urls')),
]

