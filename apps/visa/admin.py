from django.contrib import admin
from .models import Visa, VisaRequest


@admin.register(Visa)
class VisaAdmin(admin.ModelAdmin):
    list_display = ('country', 'visa_type', 'processing_time', 'cost', 'created_at')
    list_filter = ('country', 'visa_type', 'created_at')
    search_fields = ('country', 'visa_type', 'requirements')


@admin.register(VisaRequest)
class VisaRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'passport_number', 'nationality', 'destination_country', 'travel_date', 'status', 'submitted_at')
    list_filter = ('status', 'nationality', 'destination_country', 'submitted_at')
    search_fields = ('full_name', 'passport_number', 'nationality', 'destination_country')
    date_hierarchy = 'submitted_at'
    readonly_fields = ('submitted_at',)
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'passport_number', 'nationality')
        }),
        ('Travel Information', {
            'fields': ('destination_country', 'travel_date')
        }),
        ('Status', {
            'fields': ('status', 'submitted_at')
        }),
    )

