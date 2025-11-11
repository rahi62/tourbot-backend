from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'company_name',
        'is_featured_agency',
        'featured_priority',
        'is_staff',
        'date_joined',
    )
    list_filter = (
        'role',
        'is_featured_agency',
        'is_staff',
        'is_superuser',
        'is_active',
        'date_joined',
    )
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Additional Info',
            {
                'fields': (
                    'role',
                    'phone_number',
                    'company_name',
                    'agency_tagline',
                    'is_featured_agency',
                    'featured_priority',
                )
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            'Additional Info',
            {
                'fields': (
                    'role',
                    'phone_number',
                    'company_name',
                    'agency_tagline',
                    'is_featured_agency',
                    'featured_priority',
                    'email',
                    'first_name',
                    'last_name',
                )
            },
        ),
    )

