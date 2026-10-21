from django.urls import path, include

urlpatterns = [
    path('auth/', include('accounts.urls_auth')),
    path('', include('accounts.urls_profiles')),
]
