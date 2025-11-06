from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatMessageViewSet, public_chat_endpoint

router = DefaultRouter()
router.register(r'messages', ChatMessageViewSet, basename='chat-message')

urlpatterns = [
    path('', public_chat_endpoint, name='public-chat-endpoint'),  # /api/chat/ (POST)
    path('', include(router.urls)),  # /api/chat/messages/ for authenticated users
]

