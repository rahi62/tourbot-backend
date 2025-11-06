from django.contrib import admin
from .models import Tour, TourPackage


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ('title', 'destination', 'duration_days', 'price', 'is_active', 'created_at')
    list_filter = ('destination', 'is_active', 'created_at')
    search_fields = ('title', 'description', 'destination')


@admin.register(TourPackage)
class TourPackageAdmin(admin.ModelAdmin):
    list_display = ('title', 'destination_country', 'start_date', 'end_date', 'price', 'is_active')
    list_filter = ('destination_country', 'is_active', 'start_date')
    search_fields = ('title', 'description', 'destination_country')
    date_hierarchy = 'start_date'

