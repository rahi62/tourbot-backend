from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('agency', 'Agency'),
        ('traveler', 'Traveler'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='traveler')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_agency(self):
        return self.role == 'agency'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_traveler(self):
        return self.role == 'traveler'
    
    def can_manage_tours(self):
        """Check if user can create, update, or delete tours."""
        return self.role in ['admin', 'agency']
    
    def can_view_all_visa_requests(self):
        """Check if user can view all visa requests."""
        return self.role == 'admin'
    
    class Meta:
        db_table = 'users'

