from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobViewSet
from applications.views import JobApplicationsListView

router = DefaultRouter()
router.register('', JobViewSet, basename='job')

urlpatterns = [
    # Applications for a specific job: GET /api/jobs/<job_id>/applications/
    path('<int:job_id>/applications/', JobApplicationsListView.as_view(), name='job-applications-list'),
    path('', include(router.urls)),
]
