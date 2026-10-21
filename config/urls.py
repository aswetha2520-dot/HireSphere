"""
JobNest Backend Root URL Configuration.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Django Admin Site
    path('admin/', admin.site.urls),

    # Authentication & User Management APIs
    path('api/auth/', include('accounts.urls_auth')),

    # Role Profile APIs
    path('api/', include('accounts.urls_profiles')),

    # Job Management APIs
    path('api/jobs/', include('jobs.urls')),

    # Job Application APIs
    path('api/applications/', include('applications.urls')),

    # API Documentation (OpenAPI Schema, Swagger UI, ReDoc)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media and static files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
