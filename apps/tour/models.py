from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Tour(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tours', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    destination = models.CharField(max_length=100)
    duration_days = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    max_participants = models.IntegerField(default=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class TourPackage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tour_packages', null=True, blank=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    destination_country = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='tours/', blank=True, null=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.title

