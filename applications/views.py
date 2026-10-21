from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from .models import Application
from jobs.models import Job
from accounts.models import User
from .serializers import (
    ApplicationCreateSerializer,
    CandidateApplicationDetailSerializer,
    EmployerApplicationDetailSerializer,
    ApplicationStatusUpdateSerializer,
)
from .permissions import (
    IsApplicationParticipantOrAdmin,
    CanDeleteApplication,
)


class ApplicationListCreateView(APIView):
    """
    List applications based on role or submit a new application (candidate).
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        summary="List applications",
        description="Returns applications. Candidates see their own applications; Employers see applications for their posted jobs; Administrators see all applications.",
        parameters=[
            OpenApiParameter(name='status', description='Filter applications by status (e.g. PENDING, REVIEWED, SHORTLISTED, ACCEPTED, REJECTED, WITHDRAWN)', required=False, type=str),
            OpenApiParameter(name='job', description='Filter by Job ID', required=False, type=int),
        ],
        responses={200: EmployerApplicationDetailSerializer(many=True)},
        tags=["Applications"]
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        queryset = Application.objects.select_related(
            'candidate',
            'candidate__candidate_profile',
            'job',
            'job__employer',
            'job__employer__employer_profile'
        ).all()

        # Role filtering
        if user.is_staff or user.is_superuser or user.role == User.Role.ADMIN:
            pass  # Admin sees all
        elif user.role == User.Role.EMPLOYER:
            queryset = queryset.filter(job__employer=user)
        else:  # Candidate
            queryset = queryset.filter(candidate=user)

        # Query param filters
        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param.upper())

        job_param = request.query_params.get('job')
        if job_param:
            queryset = queryset.filter(job_id=job_param)

        # Choose appropriate serializer depending on user role
        if user.role == User.Role.CANDIDATE:
            serializer = CandidateApplicationDetailSerializer(queryset, many=True, context={'request': request})
        else:
            serializer = EmployerApplicationDetailSerializer(queryset, many=True, context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Submit job application",
        description="Candidates can apply for an active job. Requires a PDF resume or an existing candidate profile resume.",
        request=ApplicationCreateSerializer,
        responses={
            201: CandidateApplicationDetailSerializer,
            400: OpenApiResponse(description="Validation error (e.g. duplicate application or closed job)."),
            403: OpenApiResponse(description="Only candidates can apply.")
        },
        tags=["Applications"]
    )
    def post(self, request, *args, **kwargs):
        serializer = ApplicationCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            application = serializer.save()
            return Response(
                CandidateApplicationDetailSerializer(application, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApplicationDetailView(APIView):
    """
    Retrieve, update, or delete a single application by ID.
    """
    permission_classes = [permissions.IsAuthenticated, IsApplicationParticipantOrAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        app = get_object_or_404(
            Application.objects.select_related(
                'candidate',
                'candidate__candidate_profile',
                'job',
                'job__employer',
                'job__employer__employer_profile'
            ),
            pk=pk
        )
        self.check_object_permissions(self.request, app)
        return app

    @extend_schema(
        summary="Get application details",
        description="Retrieve application details. Candidates see application without employer notes; Employers and Admins see full details with candidate profile and notes.",
        responses={200: EmployerApplicationDetailSerializer},
        tags=["Applications"]
    )
    def get(self, request, pk, *args, **kwargs):
        app = self.get_object(pk)
        if request.user.role == User.Role.CANDIDATE:
            serializer = CandidateApplicationDetailSerializer(app, context={'request': request})
        else:
            serializer = EmployerApplicationDetailSerializer(app, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update application",
        description="Candidates can update cover_letter or set status to WITHDRAWN. Employers and Admins can update status and employer_notes.",
        request=ApplicationStatusUpdateSerializer,
        responses={200: EmployerApplicationDetailSerializer, 403: OpenApiResponse(description="Forbidden")},
        tags=["Applications"]
    )
    def patch(self, request, pk, *args, **kwargs):
        app = self.get_object(pk)
        user = request.user

        # Candidate permissions & limits
        if user.role == User.Role.CANDIDATE and app.candidate == user:
            # Candidate can only edit cover_letter or withdraw
            allowed_fields = {'cover_letter', 'status'}
            incoming_keys = set(request.data.keys())
            if not incoming_keys.issubset(allowed_fields):
                return Response(
                    {"detail": "Candidates can only update cover_letter or withdraw their application."},
                    status=status.HTTP_403_FORBIDDEN
                )

            new_status = request.data.get('status')
            if new_status and new_status.upper() != Application.Status.WITHDRAWN:
                return Response(
                    {"status": "Candidates can only change status to 'WITHDRAWN'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if 'cover_letter' in request.data:
                app.cover_letter = request.data['cover_letter']
            if new_status:
                app.status = Application.Status.WITHDRAWN
            app.save()
            return Response(
                CandidateApplicationDetailSerializer(app, context={'request': request}).data,
                status=status.HTTP_200_OK
            )

        # Employer or Admin permissions
        if (user.role == User.Role.EMPLOYER and app.job.employer == user) or user.is_staff or user.is_superuser or user.role == User.Role.ADMIN:
            serializer = ApplicationStatusUpdateSerializer(app, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    EmployerApplicationDetailSerializer(app, context={'request': request}).data,
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "You do not have permission to modify this application."}, status=status.HTTP_403_FORBIDDEN)

    @extend_schema(
        summary="Delete application",
        description="Candidates can delete their application if it is still PENDING. Administrators can delete anytime.",
        responses={204: OpenApiResponse(description="Application successfully deleted."), 403: OpenApiResponse(description="Permission denied.")},
        tags=["Applications"]
    )
    def delete(self, request, pk, *args, **kwargs):
        app = self.get_object(pk)
        user = request.user

        is_admin = user.is_staff or user.is_superuser or user.role == User.Role.ADMIN
        is_owner_pending = (app.candidate == user and app.status == Application.Status.PENDING)

        if not (is_admin or is_owner_pending):
            return Response(
                {"detail": "You can only delete an application if you are the applicant and its status is still PENDING."},
                status=status.HTTP_403_FORBIDDEN
            )

        app.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationStatusUpdateView(APIView):
    """
    Dedicated endpoint for employers to update an application status and employer notes.
    PATCH /api/applications/<id>/status/
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Update application recruitment status",
        description="Allows the job employer or admin to transition application status (REVIEWED, SHORTLISTED, INTERVIEW, ACCEPTED, REJECTED) and record internal notes.",
        request=ApplicationStatusUpdateSerializer,
        responses={
            200: EmployerApplicationDetailSerializer,
            403: OpenApiResponse(description="Permission denied. Only the employer who posted the job can update status.")
        },
        tags=["Applications"]
    )
    def patch(self, request, pk, *args, **kwargs):
        app = get_object_or_404(Application, pk=pk)
        user = request.user

        # Must be employer owner of the job or admin
        is_employer_owner = (user.role == User.Role.EMPLOYER and app.job.employer == user)
        is_admin = user.is_staff or user.is_superuser or user.role == User.Role.ADMIN

        if not (is_employer_owner or is_admin):
            return Response(
                {"detail": "Only the employer who posted this job or an administrator can update the application status."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ApplicationStatusUpdateSerializer(app, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                EmployerApplicationDetailSerializer(app, context={'request': request}).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationsListView(APIView):
    """
    List all applications submitted for a specific job.
    GET /api/jobs/<job_id>/applications/
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="List applications for a specific job",
        description="Retrieve all applications submitted for a specific job listing. Available only to the employer who posted the job or administrators.",
        parameters=[
            OpenApiParameter(name='status', description='Filter by application status', required=False, type=str),
        ],
        responses={
            200: EmployerApplicationDetailSerializer(many=True),
            403: OpenApiResponse(description="Permission denied. You can only view applications for your own job postings.")
        },
        tags=["Jobs"]
    )
    def get(self, request, job_id, *args, **kwargs):
        job = get_object_or_404(Job, pk=job_id)
        user = request.user

        is_employer_owner = (user.role == User.Role.EMPLOYER and job.employer == user)
        is_admin = user.is_staff or user.is_superuser or user.role == User.Role.ADMIN

        if not (is_employer_owner or is_admin):
            return Response(
                {"detail": "Only the employer who posted this job or an administrator can view its applications."},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = job.applications.select_related(
            'candidate',
            'candidate__candidate_profile',
            'job'
        ).all()

        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param.upper())

        serializer = EmployerApplicationDetailSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
