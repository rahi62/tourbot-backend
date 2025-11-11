from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ChatAnalyticsSummaryView,
    ChatInteractionViewSet,
    ChatLeadViewSet,
    ChatMessageViewSet,
    TourSuggestionView,
    UserPreferenceView,
    VisaKnowledgeView,
    public_chat_endpoint,
    stream_chat_endpoint,
)

router = DefaultRouter()
router.register(r'messages', ChatMessageViewSet, basename='chat-message')
router.register(r'leads', ChatLeadViewSet, basename='chat-lead')
router.register(r'interactions', ChatInteractionViewSet, basename='chat-interaction')
urlpatterns = [
    path('', public_chat_endpoint, name='public-chat-endpoint'),  # /api/chat/ (POST)
    path('stream/', stream_chat_endpoint, name='public-chat-stream-endpoint'),
    path('analytics/summary/', ChatAnalyticsSummaryView.as_view(), name='chat-analytics-summary'),
    path('preferences/', UserPreferenceView.as_view(), name='chat-preferences'),
    path('tour-suggestions/', TourSuggestionView.as_view(), name='chat-tour-suggestions'),
    path('visa-knowledge/', VisaKnowledgeView.as_view(), name='chat-visa-knowledge'),
    path('', include(router.urls)),  # /api/chat/... endpoints
]

