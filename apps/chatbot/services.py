import json
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Min, Q
from django.utils import timezone
from openai import OpenAI

from apps.tour.models import TourPackage

from .models import VisaKnowledge

UserModel = get_user_model()

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

Absolutely DO NOT handle topics خارج از حیطه تور، سفر، ویزا، یا خدمات مرتبط با تور. اگر درخواست کاربر
هیچ ارتباطی با حوزه تور و ویزا نداشت، باید مودبانه اعلام کنی که فقط در زمینه تور و ویزا می‌توانی کمک کنی و intent را "unknown" بگذاری.
"""

STRUCTURED_RESPONSE_SYSTEM_PROMPT = """
You are TourBot, an expert Persian-speaking travel consultant working within Tourbot.
Your responsibilities:
1. Discover the traveller’s intent (تور یا ویزا) by actively chatting and asking smart follow-up questions.
2. Translate vague needs into clear requirements (مقصد، بودجه، تاریخ، تعداد نفرات، هدف سفر).
3. Recommend relevant tours or visa guidance using the data provided in AVAILABLE_TOURS_JSON when—and only when—the intent is clearly tour-related.
4. Use AVAILABLE_AGENCIES_JSON to معرفی آژانس‌های مناسب (به‌ویژه برای درخواست‌های ویزا یا سفرهای شخصی‌سازی‌شده) در صورت نیاز.
5. Encourage ادامه مکالمه، ثبت درخواست، یا هدایت کاربر به جریان خرید تور/ثبت درخواست ویزا داخل توربات.

Behavioural guardrails:
- Reply in Persian unless explicitly asked otherwise.
- Mirror the user’s energy: گرم، حرفه‌ای، و پیگیر.
- Ask one targeted follow-up whenever اطلاعات ناقص است.
- Never fabricate prices یا مدارک؛ اگر مطمئن نیستی، صادقانه بگو و مسیر جایگزین ارائه کن.
- برای ویزا: گام‌بندی، مدارک کلیدی، زمان تقریبی و CTA برای ثبت درخواست در توربات بده.
- هیچ‌گاه کاربر را به «کارشناس» یا «پشتیبان انسانی» ارجاع نده؛ خودت مسئول پیشبرد فرایند هستی.
- تنها زمانی پیشنهاد تور می‌دهی که intent="tour" باشد؛ در حالت‌های دیگر suggested_tours را خالی بگذار.
- اگر پیام کاربر خارج از حوزه سفر/ویزا بود یا درخواست سرویس نامرتبط داشت، مودبانه رد کن و intent="unknown"، lead_type=null برگردان.
- خروجی را دقیقاً طبق قالب JSON درخواستی تولید کن.
"""

STRUCTURED_RESPONSE_INSTRUCTIONS = """
Produce a valid JSON object with these keys:
- intent: "tour", "visa", or "unknown" (lowercase)
- reply: string, the conversational answer in Persian
- needs_followup: boolean, true if you require more info from the user
- followup_question: string or null, a concise question in Persian if needs_followup is true
- suggested_tours: array of objects describing recommended tours (use provided tour IDs). Each object: { "id": int, "highlight": string }
- suggested_agencies: array of objects describing recommended agencies (optional). Each object: { "id": int | null, "name": string, "highlight": string }
- required_user_info: array of short strings naming any missing details you need (e.g., ["تاریخ سفر", "تعداد مسافران"])
- lead_type: "tour", "visa", or null depending on the most relevant sales path

Rules:
- If intent is "tour", you MAY populate suggested_tours using AVAILABLE_TOURS_JSON (max 3 items). Otherwise leave suggested_tours=[] and ensure highlight strings are concise.
- If intent is "visa", include یک برآورد مرحله‌ای و CTA برای ثبت درخواست ویزا در توربات.
- If intent is "unknown", politely clarify what the user is looking for, state that توربات فقط در حوزه سفر و ویزا فعال است، و set needs_followup=true.
- suggested_tours must reference IDs from the supplied context. If none are relevant, return an empty array.
- When intent is "visa" یا کاربر به دنبال مشاوره آژانس است، می‌توانی suggested_agencies را با استفاده از AVAILABLE_AGENCIES_JSON (حداکثر ۳ مورد) پر کنی؛ در غیر این صورت خالی بگذار.
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


def _compute_duration_days(tour: TourPackage) -> Optional[int]:
    try:
        if tour.start_date and tour.end_date:
            days = (tour.end_date - tour.start_date).days
            return max(days, 1)
    except Exception:
        pass
    return None


def _serialize_tour_for_model(tour: TourPackage) -> Dict[str, Any]:
    description = (tour.description or "").strip()
    short_description = description[:240] + ("..." if len(description) > 240 else "")
    duration_days = _compute_duration_days(tour)
    return {
        "id": tour.id,
        "title": tour.title,
        "destination": tour.destination_country,
        "duration_days": duration_days,
        "price": float(tour.price),
        "price_text": _format_price(tour.price),
        "start_date": tour.start_date.isoformat() if tour.start_date else None,
        "end_date": tour.end_date.isoformat() if tour.end_date else None,
        "agency": (tour.user.company_name or tour.user.get_full_name()) if tour.user else None,
        "summary": short_description,
    }


def _serialize_tour_for_client(tour: TourPackage) -> Dict[str, Any]:
    duration_days = _compute_duration_days(tour)
    return {
        "id": tour.id,
        "title": tour.title,
        "destination": tour.destination_country,
        "duration_days": duration_days,
        "price": float(tour.price),
        "price_text": _format_price(tour.price),
        "start_date": tour.start_date.isoformat() if tour.start_date else None,
        "end_date": tour.end_date.isoformat() if tour.end_date else None,
        "agency": (tour.user.company_name or tour.user.get_full_name()) if tour.user else None,
        "description": (tour.description or "")[:500],
    }


def _extract_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-zآ-ی0-9]+", text or "")
    keywords = {token.lower() for token in tokens if len(token) >= 3}
    return list(keywords)[:8]


def fetch_relevant_tours(user_message: str, limit: int = 3) -> List[TourPackage]:
    keywords = _extract_keywords(user_message)
    today = timezone.now().date()
    queryset = TourPackage.objects.filter(is_active=True, start_date__gte=today)
    if keywords:
        query = Q()
        for keyword in keywords:
            query |= Q(destination_country__icontains=keyword)
            query |= Q(title__icontains=keyword)
            query |= Q(description__icontains=keyword)
        queryset = queryset.filter(query)
    queryset = queryset.order_by("start_date")
    tours = list(queryset[:limit])
    if not tours:
        fallback_queryset = TourPackage.objects.filter(is_active=True).order_by("-start_date")
        tours = list(fallback_queryset[:limit])
    return tours


def _build_rule_based_highlight(tour: TourPackage) -> str:
    fragments: List[str] = []
    duration = _compute_duration_days(tour)
    if duration:
        fragments.append(f"{duration} روزه")
    if tour.start_date:
        fragments.append(f"حرکت {tour.start_date.strftime('%Y/%m/%d')}")
    price_text = _format_price(tour.price)
    if price_text:
        fragments.append(f"قیمت {price_text}")
    if tour.destination_country:
        fragments.append(f"مقصد {tour.destination_country}")
    if tour.user and (tour.user.company_name or tour.user.get_full_name()):
        fragments.append(f"آژانس {tour.user.company_name or tour.user.get_full_name()}")
    return " · ".join(fragments)


def _build_rule_based_reply(
    user_message: str,
    agencies_payload: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    tours = fetch_relevant_tours(user_message, limit=3)
    visa_knowledge_payload = fetch_visa_knowledge(user_message)

    if agencies_payload is None:
        agencies_payload = [
            _serialize_agency_for_model(agency)
            for agency in fetch_top_agencies(limit=3)
        ]
    top_agencies_data = agencies_payload[:3]

    agency_suggestions = [
        {
            "id": payload.get("id"),
            "display_name": payload.get("display_name"),
            "tagline": payload.get("tagline"),
            "highlight": _agency_highlight_from_payload(payload),
            "top_destinations": payload.get("top_destinations") or [],
        }
        for payload in top_agencies_data
    ]

    lowered = (user_message or "").lower()
    is_visa_request = any(
        keyword in lowered for keyword in ["visa", "ویز", "ویزا", "ویزا", "شنگن", "پاسپورت"]
    )
    is_tour_request = any(
        keyword in lowered
        for keyword in [
            "تور",
            "سفر",
            "travel",
            "tour",
            "بلیط",
            "پرواز",
            "flight",
            "hotel",
            "هتل",
        ]
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
        if agency_suggestions:
            summary_lines.append("آژانس‌های پیشنهادی برای پیگیری ویزا:")
            for agency in agency_suggestions:
                detail = agency["highlight"] or agency.get("tagline") or "آمادهٔ مشاوره اختصاصی"
                summary_lines.append(
                    f"- {agency['display_name']}: {detail}"
                )
        reply_text = (
            ("\n".join(summary_lines) + "\n") if summary_lines else ""
        ) + "برای شروع روند، جزئیات سفر و تاریخ مد نظرت را بگو تا همین حالا درخواست ویزا را در توربات ثبت کنم."
        lead_type = "visa"
        suggested_tours_for_client = []
    elif is_tour_request:
        reply_text = (
            "برای پیشنهاد تور مناسب، لطفاً مقصد دقیق، تاریخ تقریبی، تعداد نفرات و بودجه حدودی خود را بگو تا بهترین گزینه‌ها را معرفی کنم یا درخواست رزرو را ثبت کنم."
        )
        lead_type = "tour"
        suggested_tours_for_client = []
    else:
        reply_text = (
            "در حال حاضر داده دقیقی برای این پرسش ندارم، اما اگر مقصد، تاریخ و بودجه تقریبی را بگویی، همان‌جا بهترین گزینه را پیشنهاد می‌دهم یا درخواستت را ثبت می‌کنم."
        )
        lead_type = None

    return {
        "intent": "tour"
        if (suggested_tours_for_client or (lead_type == "tour"))
        else "visa"
        if lead_type == "visa"
        else "unknown",
        "reply": reply_text,
        "needs_followup": True,
        "followup_question": "مایل هستی همین الان ادامه بدهیم؟",
        "suggested_tours": suggested_tours_for_client,
        "required_user_info": ["مقصد", "تاریخ سفر", "بودجه تقریبی"],
        "lead_type": lead_type,
        "knowledge": visa_knowledge_payload,
        "suggested_agencies": agency_suggestions if lead_type == "visa" else [],
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
) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    tours = fetch_relevant_tours(user_message)
    tours_payload = [_serialize_tour_for_model(tour) for tour in tours]
    visa_knowledge_payload = fetch_visa_knowledge(user_message)
    agencies = fetch_top_agencies(limit=5)
    agencies_payload = [_serialize_agency_for_model(agency) for agency in agencies]

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
    if agencies_payload:
        messages.append(
            {
                "role": "system",
                "content": f"AVAILABLE_AGENCIES_JSON={json.dumps(agencies_payload, ensure_ascii=False)}",
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
    return messages, tours_payload, visa_knowledge_payload, agencies_payload


def generate_chatbot_reply(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    try:
        messages, tours_payload, visa_knowledge_payload, agencies_payload = _build_messages(
            user_message, conversation_history
        )

        if not getattr(settings, "OPENAI_API_KEY", None):
            return _build_rule_based_reply(user_message, agencies_payload)

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
        return _build_rule_based_reply(user_message, agencies_payload)

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
            tour_obj = TourPackage.objects.filter(id=tour_id).first()
            if tour_obj:
                suggested_tours_for_client.append({
                    **_serialize_tour_for_client(tour_obj),
                    "highlight": entry.get("highlight") or _build_rule_based_highlight(tour_obj),
                })

    agencies_map = {
        agency.get("id"): agency for agency in agencies_payload if agency.get("id") is not None
    }
    raw_agency_suggestions = data.get("suggested_agencies") or []
    suggested_agencies_for_client = []
    for entry in raw_agency_suggestions:
        if not isinstance(entry, dict):
            continue
        agency_id = entry.get("id")
        base_payload = agencies_map.get(agency_id)
        display_name = (
            entry.get("name")
            or entry.get("display_name")
            or (base_payload and base_payload.get("display_name"))
        )
        if not display_name:
            continue
        highlight = entry.get("highlight")
        if not highlight and base_payload:
            highlight = _agency_highlight_from_payload(base_payload)
        tagline = entry.get("tagline") or (base_payload and base_payload.get("tagline"))
        suggested_agencies_for_client.append(
            {
                "id": agency_id if base_payload else None,
                "display_name": display_name,
                "tagline": tagline,
                "highlight": highlight or "",
                "top_destinations": base_payload.get("top_destinations") if base_payload else [],
            }
        )

    return {
        "intent": intent,
        "reply": data.get("reply") or FALLBACK_ERROR_REPLY,
        "needs_followup": bool(data.get("needs_followup")),
        "followup_question": data.get("followup_question"),
        "suggested_tours": suggested_tours_for_client,
        "required_user_info": data.get("required_user_info") or [],
        "lead_type": data.get("lead_type"),
        "knowledge": visa_knowledge_payload,
        "suggested_agencies": suggested_agencies_for_client,
    }


def get_ai_response(user_message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    result = generate_chatbot_reply(user_message, conversation_history)
    return result.get("reply", FALLBACK_ERROR_REPLY)


def _agency_display_name(agency: UserModel) -> str:
    if agency.company_name:
        return agency.company_name
    full_name = " ".join(part for part in [agency.first_name or "", agency.last_name or ""] if part).strip()
    if full_name:
        return full_name
    return getattr(agency, "username", "آژانس ناشناس")


def _serialize_agency_for_model(agency: UserModel) -> Dict[str, Any]:
    top_destinations = list(
        agency.tour_packages.filter(is_active=True)
        .values_list("destination_country", flat=True)
        .distinct()[:3]
    )
    avg_price = getattr(agency, "avg_price", None)
    return {
        "id": agency.id,
        "display_name": _agency_display_name(agency),
        "company_name": agency.company_name,
        "tagline": getattr(agency, "agency_tagline", None),
        "is_featured": getattr(agency, "is_featured_agency", False),
        "featured_priority": getattr(agency, "featured_priority", 0),
        "active_tours": getattr(agency, "active_tours", 0) or 0,
        "featured_tours": getattr(agency, "featured_tours", 0) or 0,
        "discounted_tours": getattr(agency, "discounted_tours", 0) or 0,
        "average_price": _format_price(avg_price) if avg_price else None,
        "next_departure": (
            getattr(agency, "next_departure", None).isoformat()
            if getattr(agency, "next_departure", None)
            else None
        ),
        "top_destinations": top_destinations,
    }


def _agency_highlight_from_payload(payload: Dict[str, Any]) -> str:
    parts: List[str] = []
    top_destinations = payload.get("top_destinations") or []
    if top_destinations:
        parts.append("مقاصد: " + "، ".join(top_destinations))
    if payload.get("active_tours"):
        parts.append(f"{payload['active_tours']} تور فعال")
    if payload.get("average_price"):
        parts.append(f"میانگین قیمت {payload['average_price']}")
    if payload.get("next_departure"):
        parts.append(f"حرکت بعدی {payload['next_departure']}")
    return " • ".join(parts)


def _serialize_agency_for_client(agency: UserModel) -> Dict[str, Any]:
    serialized = _serialize_agency_for_model(agency)
    highlight = _agency_highlight_from_payload(serialized)

    return {
        "id": serialized["id"],
        "display_name": serialized["display_name"],
        "tagline": serialized["tagline"],
        "highlight": highlight,
        "top_destinations": serialized["top_destinations"],
    }


def fetch_top_agencies(limit: int = 5) -> List[UserModel]:
    today = timezone.now().date()
    queryset = (
        UserModel.objects.filter(role="agency", is_active=True)
        .annotate(
            active_tours=Count(
                "tour_packages", filter=Q(tour_packages__is_active=True)
            ),
            featured_tours=Count(
                "tour_packages",
                filter=Q(tour_packages__is_active=True, tour_packages__is_featured=True),
            ),
            discounted_tours=Count(
                "tour_packages",
                filter=Q(tour_packages__is_active=True, tour_packages__is_discounted=True),
            ),
            avg_price=Avg(
                "tour_packages__price", filter=Q(tour_packages__is_active=True)
            ),
            next_departure=Min(
                "tour_packages__start_date",
                filter=Q(
                    tour_packages__is_active=True,
                    tour_packages__start_date__gte=today,
                ),
            ),
        )
    )

    agencies = list(
        queryset.filter(active_tours__gt=0)
        .order_by(
            "-is_featured_agency",
            "featured_priority",
            "-active_tours",
            "avg_price",
        )[:limit]
    )
    return agencies

