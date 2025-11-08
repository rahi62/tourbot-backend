from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ChatAnalyticsSummaryView,
    ChatInteractionViewSet,
    ChatLeadViewSet,
    ChatMessageViewSet,
    TourSuggestionView,
    UserPreferenceView,
    public_chat_endpoint,
)

router = DefaultRouter()
router.register(r'messages', ChatMessageViewSet, basename='chat-message')
router.register(r'leads', ChatLeadViewSet, basename='chat-lead')
router.register(r'interactions', ChatInteractionViewSet, basename='chat-interaction')
urlpatterns = [
    path('', public_chat_endpoint, name='public-chat-endpoint'),  # /api/chat/ (POST)
    path('analytics/summary/', ChatAnalyticsSummaryView.as_view(), name='chat-analytics-summary'),
    path('preferences/', UserPreferenceView.as_view(), name='chat-preferences'),
    path('tour-suggestions/', TourSuggestionView.as_view(), name='chat-tour-suggestions'),
    path('', include(router.urls)),  # /api/chat/... endpoints
]

