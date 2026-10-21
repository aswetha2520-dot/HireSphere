from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse

from .models import Job
from .serializers import JobListSerializer, JobDetailSerializer, JobCreateUpdateSerializer
from .permissions import IsJobEmployerOrReadOnly
from .filters import JobFilter
from accounts.models import User


@extend_schema_view(
    list=extend_schema(
        summary="List job postings",
        description="Browse active job postings. Supports search, filtering, and ordering. Employers can view their own listings with ?my_jobs=true.",
        parameters=[
            OpenApiParameter(name='my_jobs', description='Filter to only jobs posted by the authenticated employer (boolean)', required=False, type=bool),
            OpenApiParameter(name='search', description='Search terms in title, description, skills, location, or company name', required=False, type=str),
        ],
        tags=["Jobs"]
    ),
    retrieve=extend_schema(
        summary="Get job details",
        description="Retrieve full details for a specific job posting. Public users can view active jobs; only the employer owner or admin can view inactive jobs.",
        responses={200: JobDetailSerializer, 404: OpenApiResponse(description="Job not found or access denied.")},
        tags=["Jobs"]
    ),
    create=extend_schema(
        summary="Create a new job posting",
        description="Creates a new job listing. Available only to authenticated Employers and Administrators.",
        request=JobCreateUpdateSerializer,
        responses={201: JobDetailSerializer, 403: OpenApiResponse(description="Permission denied. Only employers can create jobs.")},
        tags=["Jobs"]
    ),
    update=extend_schema(
        summary="Update a job posting",
        description="Completely update a job listing. Available only to the employer who created it or an administrator.",
        request=JobCreateUpdateSerializer,
        responses={200: JobDetailSerializer, 403: OpenApiResponse(description="Permission denied.")},
        tags=["Jobs"]
    ),
    partial_update=extend_schema(
        summary="Partially update a job posting",
        description="Partially update fields of a job listing. Available only to the employer who created it or an administrator.",
        request=JobCreateUpdateSerializer,
        responses={200: JobDetailSerializer, 403: OpenApiResponse(description="Permission denied.")},
        tags=["Jobs"]
    ),
    destroy=extend_schema(
        summary="Delete a job posting",
        description="Deletes a job listing. Available only to the employer who created it or an administrator.",
        responses={204: OpenApiResponse(description="Job successfully deleted."), 403: OpenApiResponse(description="Permission denied.")},
        tags=["Jobs"]
    ),
)
class JobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for full CRUD operations on Job listings.
    """
    queryset = Job.objects.select_related('employer', 'employer__employer_profile').all()
    permission_classes = [IsJobEmployerOrReadOnly]
    filterset_class = JobFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = [
        'title',
        'description',
        'required_skills',
        'location',
        'employer__employer_profile__company_name'
    ]
    ordering_fields = ['created_at', 'application_deadline', 'salary_min', 'salary_max', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        # Handle 'my_jobs' filter for authenticated employers
        my_jobs_param = self.request.query_params.get('my_jobs', '').lower()
        if my_jobs_param in ('true', '1') and user.is_authenticated:
            return queryset.filter(employer=user)

        # Unauthenticated users and candidates only see active jobs
        if not user.is_authenticated or user.role == User.Role.CANDIDATE:
            return queryset.filter(is_active=True)

        # Employers see all active jobs + their own jobs (even inactive)
        if user.role == User.Role.EMPLOYER:
            return queryset.filter(is_active=True) | queryset.filter(employer=user)

        # Administrators see all
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return JobListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return JobCreateUpdateSerializer
        return JobDetailSerializer

    def perform_create(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        detail_serializer = JobDetailSerializer(job, context={'request': request})
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        detail_serializer = JobDetailSerializer(job, context={'request': request})
        return Response(detail_serializer.data, status=status.HTTP_200_OK)
