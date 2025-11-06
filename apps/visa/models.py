from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Visa(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='visas', null=True, blank=True)
    country = models.CharField(max_length=100)
    visa_type = models.CharField(max_length=100)
    requirements = models.TextField()
    processing_time = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.country} - {self.visa_type}"


class VisaRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='visa_requests', null=True, blank=True)
    full_name = models.CharField(max_length=100)
    passport_number = models.CharField(max_length=20)
    nationality = models.CharField(max_length=50)
    destination_country = models.CharField(max_length=100)
    travel_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    document = models.FileField(upload_to='visa_documents/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.full_name} - {self.destination_country}"

