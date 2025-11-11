from decimal import Decimal
from datetime import date, timedelta
import hashlib
import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Avg, Count, Min, Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
from typing import List

from .models import (
    ChatInteraction,
    ChatLead,
    ChatMessage,
    Interaction,
    Offer,
    Referral,
    UserPreference,
    VisaKnowledge,
)
from .serializers import (
    ChatInteractionSerializer,
    ChatLeadSerializer,
    ChatMessageCreateSerializer,
    ChatMessageSerializer,
    InteractionSerializer,
    OfferSerializer,
    PaymentCreateSerializer,
    PaymentWebhookSerializer,
    TourSuggestionRequestSerializer,
    ReferralCreateSerializer,
    ReferralSerializer,
    UserPreferenceSerializer,
    VisaKnowledgeSerializer,
)
from .services import generate_chatbot_reply
from apps.tour.models import Tour
from apps.tour.serializers import TourSerializer
from apps.accounts.serializers import UserProfileSerializer


CHATBOT_LIMITS = {
    "authenticated": {
        "max_messages": 60,
        "window_seconds": 24 * 60 * 60,  # daily window
    },
    "anonymous": {
        "max_messages": 8,
        "window_seconds": 24 * 60 * 60,
    },
}

UNKNOWN_INTENT_THRESHOLD = 3
UNKNOWN_INTENT_WINDOW = 6 * 60 * 60  # 6 hours
BLOCK_DURATION_SECONDS = 2 * 60 * 60  # 2 hours block after repeated misuse


def _usage_cache_key(identifier: str) -> str:
    return f"chatbot:usage:{identifier}"


def _unknown_intent_cache_key(identifier: str) -> str:
    return f"chatbot:unknown:{identifier}"


def _blocked_cache_key(identifier: str) -> str:
    return f"chatbot:blocked:{identifier}"


def _client_identifier(request) -> str:
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        base = f"user:{user.pk}"
    else:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        remote_addr = forwarded_for or request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        base = f"anon:{remote_addr}:{user_agent}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _limit_reached(identifier: str, authenticated: bool) -> bool:
    limits = CHATBOT_LIMITS["authenticated" if authenticated else "anonymous"]
    key = _usage_cache_key(identifier)
    usage = cache.get(key, 0)
    return usage >= limits["max_messages"]


def _increment_usage(identifier: str, authenticated: bool) -> None:
    limits = CHATBOT_LIMITS["authenticated" if authenticated else "anonymous"]
    key = _usage_cache_key(identifier)
    usage = cache.get(key, 0) + 1
    cache.set(key, usage, timeout=limits["window_seconds"])


def _handle_unknown_intent(identifier: str) -> bool:
    key = _unknown_intent_cache_key(identifier)
    count = cache.get(key, 0) + 1
    cache.set(key, count, timeout=UNKNOWN_INTENT_WINDOW)
    if count >= UNKNOWN_INTENT_THRESHOLD:
        cache.set(_blocked_cache_key(identifier), True, timeout=BLOCK_DURATION_SECONDS)
        return True
    return False


def _reset_unknown_intent(identifier: str) -> None:
    cache.delete(_unknown_intent_cache_key(identifier))
    cache.delete(_blocked_cache_key(identifier))


def _blocked_response(message: str) -> Response:
    return Response(
        {
            "error": "chatbot_blocked",
            "reply": message,
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


def _sse_event(event_type: str, data: dict) -> str:
    return "event: {event}\ndata: {data}\n\n".format(
        event=event_type,
        data=json.dumps(data, ensure_ascii=False),
    )


def _chunk_text(text: str, chunk_size: int = 40) -> List[str]:
    if not text:
        return []
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


class IsAgencyOrAdmin(permissions.BasePermission):
    """
    Permission allowing access to authenticated users with role agency/admin
    or Django staff superusers.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False):
            return True
        return getattr(request.user, 'role', None) in ('admin', 'agency')


class ChatMessageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatMessage.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return ChatMessageCreateSerializer
        return ChatMessageSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = _client_identifier(request)
        limit_response = _check_and_block(request, identifier)
        if limit_response:
            return limit_response

        user_message = serializer.validated_data['message']

        # Get conversation history for context
        recent_messages = ChatMessage.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]

        conversation_history = [
            {
                'message': msg.message,
                'response': msg.response
            }
            for msg in reversed(recent_messages)
        ]

        # Get AI response
        ai_payload = generate_chatbot_reply(user_message, conversation_history)
        ai_response = ai_payload.get("reply", "")

        intent_value = ai_payload.get("intent") or ChatInteraction.INTENT_UNKNOWN
        if intent_value not in dict(ChatInteraction.INTENT_CHOICES):
            intent_value = ChatInteraction.INTENT_UNKNOWN

        if intent_value in {ChatInteraction.INTENT_TOUR, ChatInteraction.INTENT_VISA, ChatInteraction.INTENT_LEAD}:
            _reset_unknown_intent(identifier)
        else:
            blocked = _handle_unknown_intent(identifier)
            if blocked:
                return _blocked_response(
                    "این گفتگو خارج از حوزه تور و ویزا است. لطفاً پرسش مرتبط مطرح کنید تا ادامه دهیم."
                )

        _increment_usage(identifier, True)

        # Create the message with AI response
        message = ChatMessage.objects.create(
            user=request.user,
            message=user_message,
            response=ai_response
        )

        ChatInteraction.objects.create(
            user=request.user,
            intent=intent_value,
            raw_query=user_message,
            extracted_data={
                "required_user_info": ai_payload.get("required_user_info"),
                "suggested_tours": ai_payload.get("suggested_tours"),
                "needs_followup": ai_payload.get("needs_followup"),
                "followup_question": ai_payload.get("followup_question"),
                "lead_type": ai_payload.get("lead_type"),
                "knowledge": ai_payload.get("knowledge"),
            },
        )

        response_serializer = ChatMessageSerializer(message)
        return Response(
            {
                **response_serializer.data,
                "intent": intent_value,
                "needs_followup": ai_payload.get("needs_followup", False),
                "followup_question": ai_payload.get("followup_question"),
                "suggested_tours": ai_payload.get("suggested_tours", []),
                "required_user_info": ai_payload.get("required_user_info", []),
                "lead_type": ai_payload.get("lead_type"),
                "knowledge": ai_payload.get("knowledge", []),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def my_messages(self, request):
        messages = self.get_queryset()
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Get current user information including role.
    Alias for profile endpoint with more RESTful naming.
    """
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)


def _check_and_block(request, identifier: str) -> Response | None:
    user = getattr(request, "user", None)
    authenticated = bool(getattr(user, "is_authenticated", False))
    if cache.get(_blocked_cache_key(identifier)):
        return _blocked_response(
            "برای ادامه گفتگو، لطفاً درباره تور یا ویزا سوال بپرسید یا با ورود به حساب توربات ادامه دهید."
        )

    if _limit_reached(identifier, authenticated):
        return _blocked_response(
            "حداکثر تعداد پیام‌های مجاز امروز استفاده شده است. برای ادامه گفتگو، لطفاً وارد حساب خود شوید یا فردا دوباره تلاش کنید."
        )
    return None


@api_view(['POST'])
@permission_classes([AllowAny])
def public_chat_endpoint(request):
    """
    Public chat endpoint at /api/chat/ that accepts a message and returns AI response.
    Returns JSON: { "reply": "..." }
    """
    try:
        message = request.data.get('message', '').strip()

        if not message:
            return Response(
                {'error': 'Message field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        identifier = _client_identifier(request)
        limit_response = _check_and_block(request, identifier)
        if limit_response:
            return limit_response

        user = getattr(request, "user", None)
        authenticated = bool(getattr(user, "is_authenticated", False))

        conversation_history = []
        if authenticated:
            recent_messages = ChatMessage.objects.filter(
                user=request.user
            ).order_by('-created_at')[:10]

            conversation_history = [
                {
                    'message': msg.message,
                    'response': msg.response
                }
                for msg in reversed(recent_messages)
            ]

        ai_payload = generate_chatbot_reply(message, conversation_history if conversation_history else None)
        ai_reply = ai_payload.get("reply", "")

        _increment_usage(identifier, authenticated)

        intent_value = ai_payload.get("intent") or ChatInteraction.INTENT_UNKNOWN
        if intent_value not in dict(ChatInteraction.INTENT_CHOICES):
            intent_value = ChatInteraction.INTENT_UNKNOWN

        if intent_value in {ChatInteraction.INTENT_TOUR, ChatInteraction.INTENT_VISA, ChatInteraction.INTENT_LEAD}:
            _reset_unknown_intent(identifier)
        else:
            blocked = _handle_unknown_intent(identifier)
            if blocked:
                return _blocked_response(
                    "به نظر می‌رسد گفتگو خارج از حوزه تور و ویزا است. برای ادامه، لطفاً وارد حساب شوید یا پرسش مرتبط مطرح کنید."
                )

        if authenticated:
            ChatMessage.objects.create(
                user=request.user,
                message=message,
                response=ai_reply
            )

            ChatInteraction.objects.create(
                user=request.user,
                intent=intent_value,
                raw_query=message,
                extracted_data={
                    "required_user_info": ai_payload.get("required_user_info"),
                    "suggested_tours": ai_payload.get("suggested_tours"),
                    "needs_followup": ai_payload.get("needs_followup"),
                    "followup_question": ai_payload.get("followup_question"),
                    "lead_type": ai_payload.get("lead_type"),
                    "knowledge": ai_payload.get("knowledge"),
                },
            )

        return Response({
            'reply': ai_reply,
            'intent': intent_value,
            'needs_followup': ai_payload.get("needs_followup", False),
            'followup_question': ai_payload.get("followup_question"),
            'suggested_tours': ai_payload.get("suggested_tours", []),
            'required_user_info': ai_payload.get("required_user_info", []),
            'lead_type': ai_payload.get("lead_type"),
            'knowledge': ai_payload.get("knowledge", []),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {
                'error': 'An error occurred while processing your request',
                'reply': "متاسفم، در حال حاضر نمی‌توانم درخواست را پردازش کنم. چند لحظه دیگر دوباره تلاش کنید.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_endpoint(request):
    """
    Simple chat endpoint that accepts a message and returns AI response.
    """
    message = request.data.get('message', '').strip()

    if not message:
        return Response(
            {'error': 'Message is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    identifier = _client_identifier(request)
    limit_response = _check_and_block(request, identifier)
    if limit_response:
        return limit_response

    # Get conversation history for context
    recent_messages = ChatMessage.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]

    conversation_history = [
        {
            'message': msg.message,
            'response': msg.response
        }
        for msg in reversed(recent_messages)
    ]

    ai_payload = generate_chatbot_reply(message, conversation_history)
    ai_response = ai_payload.get("reply", "")

    _increment_usage(identifier, True)

    intent_value = ai_payload.get("intent") or ChatInteraction.INTENT_UNKNOWN
    if intent_value not in dict(ChatInteraction.INTENT_CHOICES):
        intent_value = ChatInteraction.INTENT_UNKNOWN

    if intent_value in {ChatInteraction.INTENT_TOUR, ChatInteraction.INTENT_VISA, ChatInteraction.INTENT_LEAD}:
        _reset_unknown_intent(identifier)
    else:
        blocked = _handle_unknown_intent(identifier)
        if blocked:
            return _blocked_response(
                "این گفتگو خارج از حوزه تور و ویزا است. لطفاً سوال مرتبط مطرح کنید تا ادامه دهیم."
            )

    # Save the conversation
    chat_message = ChatMessage.objects.create(
        user=request.user,
        message=message,
        response=ai_response
    )

    ChatInteraction.objects.create(
        user=request.user,
        intent=intent_value,
        raw_query=message,
        extracted_data={
            "required_user_info": ai_payload.get("required_user_info"),
            "suggested_tours": ai_payload.get("suggested_tours"),
            "needs_followup": ai_payload.get("needs_followup"),
            "followup_question": ai_payload.get("followup_question"),
            "lead_type": ai_payload.get("lead_type"),
            "knowledge": ai_payload.get("knowledge"),
        },
    )

    return Response({
        'message': chat_message.message,
        'response': chat_message.response,
        'created_at': chat_message.created_at,
        'intent': intent_value,
        'needs_followup': ai_payload.get("needs_followup", False),
        'followup_question': ai_payload.get("followup_question"),
        'suggested_tours': ai_payload.get("suggested_tours", []),
        'required_user_info': ai_payload.get("required_user_info", []),
        'lead_type': ai_payload.get("lead_type"),
        'knowledge': ai_payload.get("knowledge", []),
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def stream_chat_endpoint(request):
    message = request.data.get('message', '').strip()

    if not message:
        return Response(
            {'error': 'Message field is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    identifier = _client_identifier(request)
    limit_response = _check_and_block(request, identifier)
    if limit_response:
        return limit_response

    user = getattr(request, "user", None)
    authenticated = bool(getattr(user, "is_authenticated", False))

    conversation_history = []
    if authenticated:
        recent_messages = ChatMessage.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]

        conversation_history = [
            {
                'message': msg.message,
                'response': msg.response
            }
            for msg in reversed(recent_messages)
        ]

    ai_payload = generate_chatbot_reply(message, conversation_history if conversation_history else None)
    ai_reply = ai_payload.get("reply", "")

    intent_value = ai_payload.get("intent") or ChatInteraction.INTENT_UNKNOWN
    if intent_value not in dict(ChatInteraction.INTENT_CHOICES):
        intent_value = ChatInteraction.INTENT_UNKNOWN

    if intent_value in {ChatInteraction.INTENT_TOUR, ChatInteraction.INTENT_VISA, ChatInteraction.INTENT_LEAD}:
        _reset_unknown_intent(identifier)
    else:
        blocked = _handle_unknown_intent(identifier)
        if blocked:
            return _blocked_response(
                "به نظر می‌رسد گفتگو خارج از حوزه تور و ویزا است. برای ادامه، لطفاً وارد حساب شوید یا پرسش مرتبط مطرح کنید."
            )

    chat_message = None
    if authenticated:
        chat_message = ChatMessage.objects.create(
            user=request.user,
            message=message,
            response=ai_reply
        )

        ChatInteraction.objects.create(
            user=request.user,
            intent=intent_value,
            raw_query=message,
            extracted_data={
                "required_user_info": ai_payload.get("required_user_info"),
                "suggested_tours": ai_payload.get("suggested_tours"),
                "needs_followup": ai_payload.get("needs_followup"),
                "followup_question": ai_payload.get("followup_question"),
                "lead_type": ai_payload.get("lead_type"),
                "knowledge": ai_payload.get("knowledge"),
            },
        )

    _increment_usage(identifier, authenticated)

    suggested_tours = ai_payload.get("suggested_tours", [])
    required_user_info = ai_payload.get("required_user_info", [])
    knowledge_payload = ai_payload.get("knowledge", [])

    def event_stream():
        meta_payload = {
            "intent": intent_value,
            "needs_followup": ai_payload.get("needs_followup", False),
            "followup_question": ai_payload.get("followup_question"),
            "suggested_tours": suggested_tours,
            "required_user_info": required_user_info,
            "lead_type": ai_payload.get("lead_type"),
            "knowledge": knowledge_payload,
        }
        if chat_message:
            meta_payload["message_id"] = chat_message.id

        yield _sse_event("meta", meta_payload)

        for chunk in _chunk_text(ai_reply):
            yield _sse_event("delta", {"text": chunk})

        yield _sse_event("done", {"completed": True})

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


class ChatLeadViewSet(viewsets.ModelViewSet):
    queryset = ChatLead.objects.all()
    serializer_class = ChatLeadSerializer
    filterset_fields = ('type', 'destination')
    search_fields = ('name', 'phone', 'destination')
    ordering = ('-created_at',)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'role', None) == 'agency' or user.is_staff or user.is_superuser:
            return queryset
        # Travelers can see only their own submissions
        return queryset.filter(user=user)

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        if self.action in ('list', 'retrieve', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAgencyOrAdmin()]
        return super().get_permissions()


class ChatInteractionViewSet(viewsets.ModelViewSet):
    queryset = ChatInteraction.objects.all()
    serializer_class = ChatInteractionSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    ordering = ('-created_at',)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'role', None) in ('admin', 'agency') or user.is_staff or user.is_superuser:
            return queryset
        return queryset.filter(user=user)

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated(), IsAgencyOrAdmin()]


class ChatAnalyticsSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAgencyOrAdmin]

    def get(self, request):
        total_interactions = ChatInteraction.objects.count()
        total_leads = ChatLead.objects.count()
        tour_leads = ChatLead.objects.filter(type=ChatLead.TYPE_TOUR).count()
        visa_leads = ChatLead.objects.filter(type=ChatLead.TYPE_VISA).count()

        popular_destinations = list(
            ChatLead.objects.exclude(destination='')
            .values('destination')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        intent_distribution = list(
            ChatInteraction.objects.values('intent').annotate(count=Count('id')).order_by('-count')
        )

        conversion_rate = 0.0
        if total_interactions:
            conversion_rate = round((total_leads / total_interactions) * 100, 2)

        data = {
            'totals': {
                'interactions': total_interactions,
                'leads': total_leads,
                'tour_leads': tour_leads,
                'visa_leads': visa_leads,
                'conversion_rate_percent': conversion_rate,
            },
            'popular_destinations': popular_destinations,
            'intent_distribution': intent_distribution,
        }
        return Response(data)


class OfferViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OfferSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Offer.objects.filter(is_active=True)
        params = self.request.query_params

        is_premium = params.get('is_premium')
        if is_premium is not None:
            if is_premium.lower() in ['1', 'true', 'yes']:
                queryset = queryset.filter(is_premium=True)
            elif is_premium.lower() in ['0', 'false', 'no']:
                queryset = queryset.filter(is_premium=False)

        premium_type = params.get('premium_type')
        if premium_type:
            queryset = queryset.filter(premium_type__iexact=premium_type)

        destination = params.get('destination')
        if destination:
            queryset = queryset.filter(destination__icontains=destination)

        service_type = params.get('service_type')
        if service_type:
            queryset = queryset.filter(service_type=service_type)

        return queryset


class ReferralCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ReferralCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        referral = serializer.save()
        response_serializer = ReferralSerializer(referral)
        # Log impression upon referral creation (offer suggested)
        Interaction.objects.create(
            event=Interaction.EVENT_IMPRESSION,
            offer=referral.offer,
            referral=referral,
            referral_code=referral.code,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.data.get('session_id', ''),
            payload={'source': 'chatbot'},
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class InteractionViewSet(viewsets.ModelViewSet):
    serializer_class = InteractionSerializer
    queryset = Interaction.objects.all()

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated(), IsAgencyOrAdmin()]


class UserPreferenceView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        preference = self._find_preference(request, request.query_params)
        if not preference:
            return Response({}, status=status.HTTP_204_NO_CONTENT)
        serializer = UserPreferenceSerializer(preference)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        instance = self._find_preference(request, data)
        if instance:
            serializer = UserPreferenceSerializer(
                instance,
                data=data,
                partial=True,
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            preference = serializer.save()
            return Response(UserPreferenceSerializer(preference).data, status=status.HTTP_200_OK)

        serializer = UserPreferenceSerializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        preference = serializer.save()
        return Response(UserPreferenceSerializer(preference).data, status=status.HTTP_201_CREATED)

    def _find_preference(self, request, data):
        user = request.user if request.user.is_authenticated else None
        phone = (data or {}).get('phone') if data else None

        preference = None
        if user:
            preference = UserPreference.objects.filter(user=user).first()
        if not preference and phone:
            preference = UserPreference.objects.filter(phone=phone).first()
        return preference


class VisaKnowledgeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        country = (request.query_params.get('country') or '').strip()
        visa_type = (request.query_params.get('visa_type') or '').strip()
        try:
            limit = int(request.query_params.get('limit', 5))
        except (TypeError, ValueError):
            limit = 5
        limit = max(1, min(limit, 20))

        queryset = VisaKnowledge.objects.filter(is_active=True)
        if country:
            queryset = queryset.filter(country__icontains=country)
        if visa_type:
            queryset = queryset.filter(visa_type__icontains=visa_type)

        queryset = queryset.order_by('-last_updated', 'country', 'visa_type')[:limit]
        serializer = VisaKnowledgeSerializer(queryset, many=True)
        return Response(
            {
                'results': serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class TourSuggestionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TourSuggestionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        preference = self._find_preference(request, payload)
        combined = self._combine_preferences(preference, payload)

        if self._should_persist_preference(request, payload):
            self._persist_preference(request, preference, payload, combined)

        suggestions, used_fallback = self._build_suggestions(combined, payload.get('limit', 5))

        response_data = {
            'suggestions': TourSerializer(suggestions, many=True, context={'request': request}).data,
            'used_fallback': used_fallback,
            'criteria': {
                'favorite_destinations': combined.get('favorite_destinations'),
                'travel_style': combined.get('travel_style'),
                'budget_min': combined.get('budget_min'),
                'budget_max': combined.get('budget_max'),
            },
        }
        return Response(response_data, status=status.HTTP_200_OK)

    def _find_preference(self, request, data):
        user = request.user if request.user.is_authenticated else None
        phone = data.get('phone')
        preference = None
        if user:
            preference = UserPreference.objects.filter(user=user).first()
        if not preference and phone:
            preference = UserPreference.objects.filter(phone=phone).first()
        return preference

    def _combine_preferences(self, preference, incoming):
        combined = {
            'favorite_destinations': [],
            'travel_style': 'general',
            'budget_min': None,
            'budget_max': None,
        }

        if preference:
            combined['favorite_destinations'] = list(preference.favorite_destinations or [])
            combined['travel_style'] = preference.travel_style or 'general'
            combined['budget_min'] = preference.budget_min
            combined['budget_max'] = preference.budget_max

        incoming_favorites = incoming.get('favorite_destinations') or []
        if incoming.get('destination'):
            incoming_favorites.append(incoming['destination'])
        destinations_set = {dest.strip() for dest in combined['favorite_destinations'] if dest}
        destinations_set.update(dest.strip() for dest in incoming_favorites if dest)
        combined['favorite_destinations'] = [dest for dest in destinations_set if dest]

        travel_style = incoming.get('travel_style')
        if travel_style and travel_style != 'general':
            combined['travel_style'] = travel_style

        for key in ('budget_min', 'budget_max'):
            if incoming.get(key) is not None:
                combined[key] = incoming[key]

        return combined

    def _should_persist_preference(self, request, incoming):
        return bool(
            request.user.is_authenticated
            or incoming.get('phone')
            or incoming.get('favorite_destinations')
            or incoming.get('travel_style')
            or incoming.get('budget_min') is not None
            or incoming.get('budget_max') is not None
        )

    def _persist_preference(self, request, preference, incoming, combined):
        data = {
            'favorite_destinations': combined.get('favorite_destinations'),
            'travel_style': combined.get('travel_style'),
            'budget_min': combined.get('budget_min'),
            'budget_max': combined.get('budget_max'),
        }
        if not preference:
            data['phone'] = incoming.get('phone', '')
        serializer = UserPreferenceSerializer(
            preference,
            data=data,
            partial=preference is not None,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

    def _build_suggestions(self, combined, limit):
        qs = Tour.objects.filter(is_active=True)

        destinations = combined.get('favorite_destinations') or []
        if destinations:
            destination_query = Q()
            for dest in destinations:
                if dest:
                    destination_query |= Q(destination__icontains=dest)
            if destination_query:
                qs = qs.filter(destination_query)

        travel_style = combined.get('travel_style')
        if travel_style and travel_style != 'general':
            qs = qs.filter(travel_style=travel_style)

        budget_min = combined.get('budget_min')
        budget_max = combined.get('budget_max')
        if budget_min is not None:
            qs = qs.filter(price__gte=Decimal(budget_min))
        if budget_max is not None:
            qs = qs.filter(price__lte=Decimal(budget_max))

        qs = qs.order_by('price', '-created_at')
        suggestions = list(qs[:limit])
        used_fallback = False

        if len(suggestions) < limit:
            used_fallback = True
            fallback_qs = Tour.objects.filter(is_active=True).exclude(
                id__in=[tour.id for tour in suggestions]
            ).order_by('-created_at')
            for tour in fallback_qs:
                suggestions.append(tour)
                if len(suggestions) >= limit:
                    break

        return suggestions, used_fallback


class PaymentCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = serializer.validated_data['offer']
        referral = serializer.validated_data.get('referral')
        if referral is None:
            referral = Referral.objects.create(
                offer=offer,
                created_by=request.user if request.user.is_authenticated else None,
                metadata={'source': 'payment_create', 'session': serializer.validated_data.get('session_id')},
            )

        session_id = serializer.validated_data.get('session_id') or referral.code
        checkout_url = f'/checkout?ref={referral.code}&session={session_id}'

        Interaction.objects.create(
            event=Interaction.EVENT_CHECKOUT,
            offer=offer,
            referral=referral,
            referral_code=referral.code,
            user=request.user if request.user.is_authenticated else None,
            session_id=session_id,
            payload={'source': 'chatbot', 'amount_cents': offer.price_cents},
        )

        return Response(
            {
                'checkout_url': checkout_url,
                'referral_code': referral.code,
                'session_id': session_id,
                'amount_cents': offer.price_cents,
            },
            status=status.HTTP_200_OK,
        )


class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PaymentWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral = serializer.validated_data['referral']
        status_value = serializer.validated_data['status']
        payload = serializer.validated_data.get('payload', {})

        event = (
            Interaction.EVENT_PAYMENT_SUCCESS
            if status_value == 'success'
            else Interaction.EVENT_PAYMENT_FAILED
        )

        Interaction.objects.create(
            event=event,
            offer=referral.offer,
            referral=referral,
            referral_code=referral.code,
            session_id=payload.get('session_id', ''),
            payload=payload,
        )

        return Response({'status': 'ok', 'event': event}, status=status.HTTP_200_OK)


