from django.urls import path
from .views import register, profile, update_profile, CustomTokenObtainPairView, me

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('profile/', profile, name='profile'),
    path('profile/update/', update_profile, name='update-profile'),
    path('me/', me, name='me'),  # Alias for profile endpoint
]

