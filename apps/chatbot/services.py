import json
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.db.models import Q
from openai import OpenAI

from apps.tour.models import Tour

# Initialize OpenAI client (lazy initialization)
def get_openai_client():
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set in Django settings")
    return OpenAI(api_key=api_key)

STRUCTURED_RESPONSE_SYSTEM_PROMPT = """
You are TourBot, an experienced Persian-speaking travel assistant for a tour and visa platform.
Your job is to understand the user's intent (tour planning vs visa questions), provide precise
and trustworthy guidance, and encourage them to take the next step with the agency.

Strict rules:
- Always reply in Persian (fa-IR) unless the user explicitly requests another language.
- Be enthusiastic yet professional. Use a warm tone suited for a premium travel consultant.
- When the user intent is unclear, ask exactly one focused follow-up question.
- Never invent information that is not provided. If unsure, say so and suggest contacting an expert.
- If tour data is provided, reference the options by name and highlight why they fit the user.
- If visa guidance is requested, outline steps, required documents, timelines, and practical tips.
- Promote booking or consultation gently when it makes sense (e.g., suggesting a call, submitting a form).
- Respect structured JSON output exactly as requested.
"""

STRUCTURED_RESPONSE_INSTRUCTIONS = """
Produce a valid JSON object with these keys:
- intent: "tour", "visa", or "unknown" (lowercase)
- reply: string, the conversational answer in Persian
- needs_followup: boolean, true if you require more info from the user
- followup_question: string or null, a concise question in Persian if needs_followup is true
- suggested_tours: array of objects describing recommended tours (use provided tour IDs). Each object: { "id": int, "highlight": string }
- required_user_info: array of short strings naming any missing details you need (e.g., ["تاریخ سفر", "تعداد مسافران"])
- lead_type: "tour", "visa", or null depending on the most relevant sales path

Rules:
- If intent is "tour", prioritize the provided tours (if any) and explain why they match the request.
- If intent is "visa", include a step-by-step outline (overview) and note if a specialist should follow up.
- If intent is "unknown", politely clarify what the user is looking for and set needs_followup=true.
- suggested_tours must reference IDs from the supplied context. If none are relevant, return an empty array.
- Do not add extra top-level keys.
"""

FALLBACK_ERROR_REPLY = "متاسفم، در حال حاضر نمی‌توانم پاسخ دقیقی ارائه دهم. لطفاً بعداً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."


def _format_price(value: Decimal) -> str:
    try:
        numeric = Decimal(value)
    except Exception:
        return ""
    try:
        integer_value = int(numeric)
    except Exception:
        integer_value = 0
    return f"{integer_value:,} تومان"


def _serialize_tour_for_model(tour: Tour) -> Dict[str, Any]:
    description = (tour.description or "").strip()
    short_description = description[:240] + ("..." if len(description) > 240 else "")
    return {
        "id": tour.id,
        "title": tour.title,
        "destination": tour.destination,
        "duration_days": tour.duration_days,
        "price": float(tour.price),
        "price_text": _format_price(tour.price),
        "travel_style": tour.travel_style,
        "summary": short_description,
    }


def _serialize_tour_for_client(tour: Tour) -> Dict[str, Any]:
    return {
        "id": tour.id,
        "title": tour.title,
        "destination": tour.destination,
        "duration_days": tour.duration_days,
        "price": float(tour.price),
        "price_text": _format_price(tour.price),
        "travel_style": tour.travel_style,
        "description": tour.description[:500] if tour.description else "",
    }


def _extract_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-zآ-ی0-9]+", text or "")
    keywords = {token.lower() for token in tokens if len(token) >= 3}
    return list(keywords)[:8]


def fetch_relevant_tours(user_message: str, limit: int = 3) -> List[Tour]:
    keywords = _extract_keywords(user_message)
    queryset = Tour.objects.filter(is_active=True)
    if keywords:
        query = Q()
        for keyword in keywords:
            query |= Q(destination__icontains=keyword)
            query |= Q(title__icontains=keyword)
            query |= Q(description__icontains=keyword)
        queryset = queryset.filter(query)
    queryset = queryset.order_by('-created_at')
    tours = list(queryset[:limit])
    if not tours:
        tours = list(Tour.objects.filter(is_active=True).order_by('-created_at')[:limit])
    return tours


def _build_messages(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
    tours = fetch_relevant_tours(user_message)
    tours_payload = [_serialize_tour_for_model(tour) for tour in tours]

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": STRUCTURED_RESPONSE_SYSTEM_PROMPT.strip()},
        {
            "role": "system",
            "content": f"AVAILABLE_TOURS_JSON={json.dumps(tours_payload, ensure_ascii=False)}",
        },
        {"role": "system", "content": STRUCTURED_RESPONSE_INSTRUCTIONS.strip()},
    ]

    if conversation_history:
        for msg in conversation_history[-10:]:
            user_text = msg.get('message', '').strip()
            if user_text:
                messages.append({"role": "user", "content": user_text})
            bot_text = msg.get('response', '').strip()
            if bot_text:
                messages.append({"role": "assistant", "content": bot_text})

    messages.append({"role": "user", "content": user_message})
    return messages, tours_payload


def generate_chatbot_reply(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    try:
        messages, tours_payload = _build_messages(user_message, conversation_history)
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("OpenAI structured response error: %s", exc, exc_info=True)
        return {
            "intent": "unknown",
            "reply": FALLBACK_ERROR_REPLY,
            "needs_followup": False,
            "followup_question": None,
            "suggested_tours": [],
            "required_user_info": [],
            "lead_type": None,
        }

    intent = (data.get("intent") or "unknown").lower()
    if intent not in {"tour", "visa", "unknown"}:
        intent = "unknown"

    suggested = data.get("suggested_tours") or []
    valid_ids = {tour["id"] for tour in tours_payload}
    filtered_suggestions = [
        item for item in suggested
        if isinstance(item, dict) and item.get("id") in valid_ids
    ]

    tours_map = {tour["id"]: tour for tour in tours_payload}
    suggested_tours_for_client = []
    for entry in filtered_suggestions:
        tour_id = entry.get("id")
        if tour_id in tours_map:
            tour_obj = Tour.objects.filter(id=tour_id).first()
            if tour_obj:
                suggested_tours_for_client.append({
                    **_serialize_tour_for_client(tour_obj),
                    "highlight": entry.get("highlight") or "",
                })

    return {
        "intent": intent,
        "reply": data.get("reply") or FALLBACK_ERROR_REPLY,
        "needs_followup": bool(data.get("needs_followup")),
        "followup_question": data.get("followup_question"),
        "suggested_tours": suggested_tours_for_client,
        "required_user_info": data.get("required_user_info") or [],
        "lead_type": data.get("lead_type"),
    }


def get_ai_response(user_message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    result = generate_chatbot_reply(user_message, conversation_history)
    return result.get("reply", FALLBACK_ERROR_REPLY)

