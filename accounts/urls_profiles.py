from django.urls import path
from .views import CandidateProfileView, EmployerProfileView

urlpatterns = [
    path('candidates/me/', CandidateProfileView.as_view(), name='candidate-profile-me'),
    path('employers/me/', EmployerProfileView.as_view(), name='employer-profile-me'),
]
