import os
from openai import OpenAI
from django.conf import settings

# Initialize OpenAI client (lazy initialization)
def get_openai_client():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)

# Travel assistant system prompt
TRAVEL_ASSISTANT_PROMPT = """You are TourBot, a friendly and enthusiastic AI travel assistant for a travel booking platform. Your primary goals are:

1. Answer questions about visa requirements and application procedures
2. Provide information about available tour packages and destinations
3. Help users with travel planning and recommendations
4. Persuade users to book tours and services through the platform

Key Guidelines:
- Be warm, friendly, and enthusiastic about travel
- When discussing tours or destinations, highlight the benefits and unique experiences
- Naturally encourage bookings by emphasizing value, convenience, and memorable experiences
- Provide accurate information about visa requirements and travel logistics
- Ask follow-up questions to understand user needs and suggest relevant tours
- Use positive language and create excitement about travel opportunities
- Be helpful first, then gently guide conversations toward booking opportunities
- Use emojis sparingly to make responses more engaging
- Always maintain honesty and provide accurate information

Remember: Your goal is to be genuinely helpful while naturally encouraging users to book through the platform. Focus on creating desire and showing value, not being pushy."""


def get_ai_response(user_message: str, conversation_history: list = None) -> str:
    """
    Get AI response from OpenAI GPT API.
    
    Args:
        user_message: The user's message
        conversation_history: Optional list of previous messages for context
        
    Returns:
        AI response string
    """
    try:
        # Build messages array
        messages = [
            {"role": "system", "content": TRAVEL_ASSISTANT_PROMPT}
        ]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-10:]:  # Keep last 10 messages for context
                messages.append({"role": "user", "content": msg.get('message', '')})
                if msg.get('response'):
                    messages.append({"role": "assistant", "content": msg.get('response', '')})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Call OpenAI API
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        # Log the error for debugging but don't expose it to the user
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"OpenAI API error: {str(e)}")
        # Return a friendly error message without exposing the actual error
        return "I apologize, but I'm having trouble processing your request right now. Please try again later."

