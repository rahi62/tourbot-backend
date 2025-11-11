import json
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.db.models import Q
from openai import OpenAI

from apps.tour.models import Tour

from .models import VisaKnowledge

# Initialize OpenAI client (lazy initialization)
def get_openai_client():
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set in Django settings")
    return OpenAI(api_key=api_key)

BUSINESS_PROFILE_CONTEXT = """
You are embedded inside Tourbot, an Iranian travel-tech assistant that works for a premium travel
and visa agency. The agency offers curated outbound tours (e.g. استانبول، دبی، ارمنستان، اروپا),
custom honeymoon and family packages, and professional visa consultation (شنگن، کانادا، انگلستان، آسیای شرقی).
Typical clients expect concierge-style service: they want clarity on مدارک، زمان‌بندی، هزینه، و ارزش پکیج.

Core services Tourbot must represent:
- مشاوره و رزرو تورهای تفریحی و تجاری (economy تا لوکس)
- خدمات ویژه سفر (هتل، پرواز، بیمه، ترانسفر، تورهای اختیاری)
- مشاوره ویزا برای مقاصد محبوب، همراه با چک‌لیست مدارک و پیگیری کارشناسان
- پیگیری و تبدیل کاربر به لید از طریق فرم تماس یا ارجاع به پشتیبانی
"""

STRUCTURED_RESPONSE_SYSTEM_PROMPT = """
You are TourBot, an expert Persian-speaking travel consultant working within Tourbot.
Your responsibilities:
1. Discover the traveller’s intent (تور یا ویزا) by actively chatting and asking smart follow-up questions.
2. Translate vague needs into clear requirements (مقصد، بودجه، تاریخ، تعداد نفرات، هدف سفر).
3. Recommend relevant tours or visa guidance using the data provided in AVAILABLE_TOURS_JSON when—and only when—the intent is clearly tour-related.
4. Encourage ادامه مکالمه، ثبت درخواست، یا هدایت کاربر به جریان خرید تور/ثبت درخواست ویزا داخل توربات.

Behavioural guardrails:
- Reply in Persian unless explicitly asked otherwise.
- Mirror the user’s energy: گرم، حرفه‌ای، و پیگیر.
- Ask one targeted follow-up whenever اطلاعات ناقص است.
- Never fabricate prices یا مدارک؛ اگر مطمئن نیستی، صادقانه بگو و مسیر جایگزین ارائه کن.
- برای ویزا: گام‌بندی، مدارک کلیدی، زمان تقریبی و CTA برای ثبت درخواست در توربات بده.
- هیچ‌گاه کاربر را به «کارشناس» یا «پشتیبان انسانی» ارجاع نده؛ خودت مسئول پیشبرد فرایند هستی.
- تنها زمانی پیشنهاد تور می‌دهی که intent="tour" باشد؛ در حالت‌های دیگر suggested_tours را خالی بگذار.
- خروجی را دقیقاً طبق قالب JSON درخواستی تولید کن.
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
- If intent is "tour", you MAY populate suggested_tours using AVAILABLE_TOURS_JSON (max 3 items). Otherwise leave suggested_tours=[] and ensure highlight strings are concise.
- If intent is "visa", include یک برآورد مرحله‌ای و CTA برای ثبت درخواست ویزا در توربات.
- If intent is "unknown", politely clarify what the user is looking for and set needs_followup=true.
- suggested_tours must reference IDs from the supplied context. If none are relevant, return an empty array.
- Do not add extra top-level keys.
"""

FALLBACK_ERROR_REPLY = "متاسفم، در حال حاضر نمی‌توانم پاسخ دقیقی ارائه دهم. لطفاً بعداً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
RULE_BASED_REPLY_INTRO = (
    "من ربات هوشمند توربات هستم و در حال حاضر به سرویس هوش مصنوعی متصل نیستم، "
    "اما با توجه به اطلاعاتی که دارم این پیشنهادها می‌تواند برای شما مناسب باشد:"
)


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


def _build_rule_based_highlight(tour: Tour) -> str:
    fragments: List[str] = []
    if tour.duration_days:
        fragments.append(f"{tour.duration_days} روزه")
    price_text = _format_price(tour.price)
    if price_text:
        fragments.append(f"قیمت {price_text}")
    if tour.destination:
        fragments.append(f"مقصد {tour.destination}")
    return " · ".join(fragments)


def _build_rule_based_reply(
    user_message: str,
) -> Dict[str, Any]:
    tours = fetch_relevant_tours(user_message, limit=3)
    visa_knowledge_payload = fetch_visa_knowledge(user_message)

    lowered = (user_message or "").lower()
    is_visa_request = any(
        keyword in lowered for keyword in ["visa", "ویز", "ویزا", "ویزا", "شنگن", "پاسپورت"]
    )

    suggested_tours_for_client = []
    for tour in tours:
        suggested_tours_for_client.append(
            {
                **_serialize_tour_for_client(tour),
                "highlight": _build_rule_based_highlight(tour),
            }
        )

    if not is_visa_request and suggested_tours_for_client:
        reply_parts = [RULE_BASED_REPLY_INTRO]
        for idx, tour in enumerate(suggested_tours_for_client, start=1):
            reply_parts.append(
                f"{idx}. {tour['title']} ({tour['highlight']})"
            )
        reply_parts.append(
            "اگر نیاز به اطلاعات بیشتری دارید یا قصد رزرو دارید، می‌توانم درخواست شما را ثبت کنم."
        )
        reply_text = "\n".join(reply_parts)
        lead_type = "tour"
    elif is_visa_request or visa_knowledge_payload:
        summary_lines = []
        if visa_knowledge_payload:
            summary_lines.append("راهنمای سریع ویزا:")
            for entry in visa_knowledge_payload:
                summary_lines.append(
                    f"- {entry['country']} ({entry.get('visa_type') or 'ویزای رایج'}): {entry['summary']}"
                )
        reply_text = (
            ("\n".join(summary_lines) + "\n") if summary_lines else ""
        ) + "برای شروع روند، جزئیات سفر و تاریخ مد نظرت را بگو تا همین حالا درخواست ویزا را در توربات ثبت کنم."
        lead_type = "visa"
        suggested_tours_for_client = []
    else:
        reply_text = (
            "در حال حاضر داده دقیقی برای این پرسش ندارم، اما اگر مقصد، تاریخ و بودجه تقریبی را بگویی، همان‌جا بهترین گزینه را پیشنهاد می‌دهم یا درخواستت را ثبت می‌کنم."
        )
        lead_type = None

    return {
        "intent": "unknown" if not lead_type and not suggested_tours_for_client else ("tour" if suggested_tours_for_client else "visa" if lead_type == "visa" else "unknown"),
        "reply": reply_text,
        "needs_followup": True,
        "followup_question": "مایل هستی همین الان ادامه بدهیم؟",
        "suggested_tours": suggested_tours_for_client,
        "required_user_info": ["مقصد", "تاریخ سفر", "بودجه تقریبی"],
        "lead_type": lead_type,
        "knowledge": visa_knowledge_payload,
    }


def _serialize_visa_knowledge(entry: VisaKnowledge) -> Dict[str, Any]:
    return {
        "country": entry.country,
        "visa_type": entry.visa_type or "",
        "summary": entry.summary,
        "requirements": entry.requirements or [],
        "processing_time": entry.processing_time,
        "notes": entry.notes,
        "source_url": entry.source_url,
        "last_updated": entry.last_updated.isoformat(),
    }


def fetch_visa_knowledge(user_message: str, limit: int = 3) -> List[Dict[str, Any]]:
    keywords = _extract_keywords(user_message)
    queryset = VisaKnowledge.objects.filter(is_active=True)
    if keywords:
        query = Q()
        for keyword in keywords:
            query |= Q(country__icontains=keyword)
            query |= Q(visa_type__icontains=keyword)
        queryset = queryset.filter(query)
    queryset = queryset.order_by('-last_updated', 'country', 'visa_type')[:limit]
    return [_serialize_visa_knowledge(entry) for entry in queryset]


def _build_messages(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    tours = fetch_relevant_tours(user_message)
    tours_payload = [_serialize_tour_for_model(tour) for tour in tours]
    visa_knowledge_payload = fetch_visa_knowledge(user_message)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": BUSINESS_PROFILE_CONTEXT.strip()},
        {"role": "system", "content": STRUCTURED_RESPONSE_SYSTEM_PROMPT.strip()},
        {
            "role": "system",
            "content": f"AVAILABLE_TOURS_JSON={json.dumps(tours_payload, ensure_ascii=False)}",
        },
    ]
    if visa_knowledge_payload:
        messages.append(
            {
                "role": "system",
                "content": f"AVAILABLE_VISA_KNOWLEDGE_JSON={json.dumps(visa_knowledge_payload, ensure_ascii=False)}",
            }
        )
    messages.append({"role": "system", "content": STRUCTURED_RESPONSE_INSTRUCTIONS.strip()})

    if conversation_history:
        for msg in conversation_history[-10:]:
            user_text = msg.get('message', '').strip()
            if user_text:
                messages.append({"role": "user", "content": user_text})
            bot_text = msg.get('response', '').strip()
            if bot_text:
                messages.append({"role": "assistant", "content": bot_text})

    messages.append({"role": "user", "content": user_message})
    return messages, tours_payload, visa_knowledge_payload


def generate_chatbot_reply(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    try:
        messages, tours_payload, visa_knowledge_payload = _build_messages(
            user_message, conversation_history
        )

        if not getattr(settings, "OPENAI_API_KEY", None):
            return _build_rule_based_reply(user_message)

        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=700,
            timeout=30,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
    except Exception as exc:
        import logging

        logger = logging.getLogger(__name__)
        logger.error("OpenAI structured response error: %s", exc, exc_info=True)
        return _build_rule_based_reply(user_message)

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
        "knowledge": visa_knowledge_payload,
    }


def get_ai_response(user_message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    result = generate_chatbot_reply(user_message, conversation_history)
    return result.get("reply", FALLBACK_ERROR_REPLY)

