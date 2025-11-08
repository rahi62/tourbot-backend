from decimal import Decimal

from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    ChatInteraction,
    ChatLead,
    ChatMessage,
    Interaction,
    Offer,
    Referral,
    UserPreference,
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
)
from .services import generate_chatbot_reply
from apps.tour.models import Tour
from apps.tour.serializers import TourSerializer


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
        
        # Create the message with AI response
        message = ChatMessage.objects.create(
            user=request.user,
            message=user_message,
            response=ai_response
        )
        
        intent_value = ai_payload.get("intent") or ChatInteraction.INTENT_UNKNOWN
        if intent_value not in dict(ChatInteraction.INTENT_CHOICES):
            intent_value = ChatInteraction.INTENT_UNKNOWN

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
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def my_messages(self, request):
        messages = self.get_queryset()
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)


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
    ai_payload = generate_chatbot_reply(message, conversation_history)
    ai_response = ai_payload.get("reply", "")
    
    # Save the conversation
    chat_message = ChatMessage.objects.create(
        user=request.user,
        message=message,
        response=ai_response
    )
    
    intent_value = ai_payload.get("intent") or ChatInteraction.INTENT_UNKNOWN
    if intent_value not in dict(ChatInteraction.INTENT_CHOICES):
        intent_value = ChatInteraction.INTENT_UNKNOWN

    if request.user.is_authenticated:
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
    }, status=status.HTTP_200_OK)


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
        
        # Get conversation history if user is authenticated
        conversation_history = []
        if request.user.is_authenticated:
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
        ai_payload = generate_chatbot_reply(message, conversation_history if conversation_history else None)
        ai_reply = ai_payload.get("reply", "")
        
        # Save the conversation if user is authenticated
        if request.user.is_authenticated:
            ChatMessage.objects.create(
                user=request.user,
                message=message,
                response=ai_reply
            )
        
        intent_value = ai_payload.get("intent") or ChatInteraction.INTENT_UNKNOWN
        if intent_value not in dict(ChatInteraction.INTENT_CHOICES):
            intent_value = ChatInteraction.INTENT_UNKNOWN

        if request.user.is_authenticated:
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
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # Handle errors gracefully
        return Response(
            {
                'error': 'An error occurred while processing your request',
                'reply': "I apologize, but I'm having trouble processing your request right now. Please try again later."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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


