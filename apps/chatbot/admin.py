from django.contrib import admin

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


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('message', 'response', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(ChatLead)
class ChatLeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'type', 'destination', 'budget', 'travel_date', 'created_at')
    list_filter = ('type', 'destination', 'created_at')
    search_fields = ('name', 'phone', 'destination')
    readonly_fields = ('created_at',)


@admin.register(ChatInteraction)
class ChatInteractionAdmin(admin.ModelAdmin):
    list_display = ('intent', 'user', 'created_at')
    list_filter = ('intent', 'created_at')
    search_fields = ('raw_query', 'extracted_data')
    readonly_fields = ('created_at',)


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'service_type', 'destination', 'is_premium', 'premium_type', 'price_cents', 'created_at')
    list_filter = ('service_type', 'is_premium', 'premium_type', 'destination', 'created_at')
    search_fields = ('title', 'slug', 'destination', 'premium_type')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('code', 'offer', 'created_by', 'created_at', 'expires_at')
    list_filter = ('offer__service_type', 'offer__premium_type', 'created_at')
    search_fields = ('code', 'offer__title')
    readonly_fields = ('code', 'created_at')


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('event', 'offer', 'referral', 'user', 'session_id', 'created_at')
    list_filter = ('event', 'offer__service_type', 'offer__premium_type', 'created_at')
    search_fields = ('offer__title', 'referral__code', 'session_id')
    readonly_fields = ('created_at',)


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'travel_style', 'budget_min', 'budget_max', 'updated_at')
    search_fields = ('phone', 'user__username')
    list_filter = ('travel_style',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(VisaKnowledge)
class VisaKnowledgeAdmin(admin.ModelAdmin):
    list_display = ('country', 'visa_type', 'processing_time', 'is_active', 'last_updated')
    list_filter = ('is_active', 'country', 'visa_type')
    search_fields = ('country', 'visa_type', 'summary', 'notes')
    readonly_fields = ('last_updated',)

