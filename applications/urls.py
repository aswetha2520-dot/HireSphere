from django.urls import path
from .views import (
    ApplicationListCreateView,
    ApplicationDetailView,
    ApplicationStatusUpdateView,
)

urlpatterns = [
    # Application collection endpoints
    path('', ApplicationListCreateView.as_view(), name='application-list-create'),

    # Single application endpoints
    path('<int:pk>/', ApplicationDetailView.as_view(), name='application-detail'),

    # Dedicated status update endpoint for employers: /api/applications/<id>/status/
    path('<int:pk>/status/', ApplicationStatusUpdateView.as_view(), name='application-status-update'),
]
