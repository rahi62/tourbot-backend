from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from .models import ChatMessage
from .serializers import ChatMessageSerializer, ChatMessageCreateSerializer
from .services import get_ai_response


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
        ai_response = get_ai_response(user_message, conversation_history)
        
        # Create the message with AI response
        message = ChatMessage.objects.create(
            user=request.user,
            message=user_message,
            response=ai_response
        )
        
        response_serializer = ChatMessageSerializer(message)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

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
    ai_response = get_ai_response(message, conversation_history)
    
    # Save the conversation
    chat_message = ChatMessage.objects.create(
        user=request.user,
        message=message,
        response=ai_response
    )
    
    return Response({
        'message': chat_message.message,
        'response': chat_message.response,
        'created_at': chat_message.created_at,
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
        ai_reply = get_ai_response(message, conversation_history if conversation_history else None)
        
        # Save the conversation if user is authenticated
        if request.user.is_authenticated:
            ChatMessage.objects.create(
                user=request.user,
                message=message,
                response=ai_reply
            )
        
        return Response({
            'reply': ai_reply
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

