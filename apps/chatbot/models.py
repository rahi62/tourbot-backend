import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.db import models

from apps.tour.constants import TRAVEL_STYLE_CHOICES
from django.utils import timezone


class ChatMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        null=True,
        blank=True,
    )
    message = models.TextField()
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        user_part = self.user.username if self.user else 'anonymous'
        return f'{user_part} - {self.message[:50]}'


class ChatLead(models.Model):
    TYPE_TOUR = 'tour'
    TYPE_VISA = 'visa'
    TYPE_CHOICES = [
        (TYPE_TOUR, 'Tour'),
        (TYPE_VISA, 'Visa'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='chat_leads',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=50)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    destination = models.CharField(max_length=160, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    travel_date = models.DateField(null=True, blank=True)
    message = models.TextField(blank=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_type_display()}) - {self.destination or "N/A"}'


class ChatInteraction(models.Model):
    INTENT_TOUR = 'tour'
    INTENT_VISA = 'visa'
    INTENT_LEAD = 'lead'
    INTENT_UNKNOWN = 'unknown'

    INTENT_CHOICES = [
        (INTENT_TOUR, 'Tour'),
        (INTENT_VISA, 'Visa'),
        (INTENT_LEAD, 'Lead'),
        (INTENT_UNKNOWN, 'Unknown'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='chat_interactions',
        null=True,
        blank=True,
    )
    intent = models.CharField(max_length=32, choices=INTENT_CHOICES, default=INTENT_UNKNOWN)
    raw_query = models.TextField()
    extracted_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.intent} - {self.raw_query[:40]}'


class Offer(models.Model):
    SERVICE_TOUR = 'tour'
    SERVICE_VISA = 'visa'
    SERVICE_CHOICES = [
        (SERVICE_TOUR, 'Tour'),
        (SERVICE_VISA, 'Visa'),
    ]

    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    destination = models.CharField(max_length=120, blank=True)
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES, default=SERVICE_TOUR)
    is_premium = models.BooleanField(default=False)
    premium_type = models.CharField(max_length=50, blank=True)
    price_cents = models.PositiveIntegerField(default=0)
    image_url = models.URLField(blank=True)
    metadata = models.JSONField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


def generate_referral_code(length: int = 10) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class Referral(models.Model):
    code = models.CharField(max_length=20, unique=True, editable=False)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='referrals')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_referrals',
    )
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_referral_code()
        if self.expires_at is None:
            self.expires_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.code} -> {self.offer}'


class Interaction(models.Model):
    EVENT_IMPRESSION = 'impression'
    EVENT_CLICK = 'click'
    EVENT_CHECKOUT = 'checkout_start'
    EVENT_PAYMENT_SUCCESS = 'payment_success'
    EVENT_PAYMENT_FAILED = 'payment_failed'

    EVENT_CHOICES = [
        (EVENT_IMPRESSION, 'Impression'),
        (EVENT_CLICK, 'Click'),
        (EVENT_CHECKOUT, 'Checkout Start'),
        (EVENT_PAYMENT_SUCCESS, 'Payment Success'),
        (EVENT_PAYMENT_FAILED, 'Payment Failed'),
    ]

    event = models.CharField(max_length=32, choices=EVENT_CHOICES)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='interactions')
    referral = models.ForeignKey(
        Referral,
        on_delete=models.SET_NULL,
        related_name='interactions',
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='offer_interactions',
        null=True,
        blank=True,
    )
    session_id = models.CharField(max_length=64, blank=True)
    referral_code = models.CharField(max_length=20, blank=True)
    payload = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event} - {self.offer} - {self.created_at}'


class UserPreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='chat_preferences',
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=20, blank=True, default='')
    favorite_destinations = models.JSONField(blank=True, default=list)
    travel_style = models.CharField(
        max_length=20,
        choices=TRAVEL_STYLE_CHOICES,
        default='general',
    )
    budget_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                name='unique_user_preference',
                condition=models.Q(user__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['phone'],
                name='unique_phone_preference',
                condition=models.Q(phone__gt=''),
            ),
        ]

    def __str__(self):
        identifier = self.user.username if self.user else self.phone or 'anonymous'
        return f'Preference for {identifier}'

    @property
    def has_budget_range(self) -> bool:
        return self.budget_min is not None or self.budget_max is not None

