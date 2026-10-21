from rest_framework import serializers
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Application
from jobs.models import Job
from accounts.models import User, CandidateProfile
from accounts.validators import validate_resume_file


class CandidateNestedSerializer(serializers.Serializer):
    """
    Candidate details displayed to employers reviewing an application.
    """
    id = serializers.IntegerField(source='candidate.id', read_only=True)
    email = serializers.EmailField(source='candidate.email', read_only=True)
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    def _get_profile(self, obj):
        return getattr(obj.candidate, 'candidate_profile', None)

    @extend_schema_field(OpenApiTypes.STR)
    def get_full_name(self, obj):
        profile = self._get_profile(obj)
        return profile.full_name if profile and profile.full_name else obj.candidate.full_name

    @extend_schema_field(OpenApiTypes.STR)
    def get_phone_number(self, obj):
        profile = self._get_profile(obj)
        return profile.phone_number if profile else ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_location(self, obj):
        profile = self._get_profile(obj)
        return profile.location if profile else ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_skills(self, obj):
        profile = self._get_profile(obj)
        return profile.skills if profile else ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_education(self, obj):
        profile = self._get_profile(obj)
        return profile.education if profile else ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_experience(self, obj):
        profile = self._get_profile(obj)
        return profile.experience if profile else ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_profile_picture(self, obj):
        request = self.context.get('request')
        profile = self._get_profile(obj)
        if profile and profile.profile_picture:
            url = profile.profile_picture.url
            return request.build_absolute_uri(url) if request else url
        return None


class JobNestedSerializer(serializers.ModelSerializer):
    """
    Compact job information for applications.
    """
    company_name = serializers.CharField(read_only=True)

    class Meta:
        model = Job
        fields = [
            'id',
            'title',
            'company_name',
            'location',
            'employment_type',
            'remote_status',
            'salary_min',
            'salary_max',
            'is_active',
        ]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for Candidates submitting a job application.
    """
    job = serializers.PrimaryKeyRelatedField(queryset=Job.objects.all(), required=True)
    resume = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Application
        fields = [
            'id',
            'job',
            'resume',
            'cover_letter',
            'status',
            'applied_date',
        ]
        read_only_fields = ['id', 'status', 'applied_date']

    def validate_resume(self, value):
        if value:
            validate_resume_file(value)
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        job = attrs.get('job')

        # Check candidate role
        if user.role != User.Role.CANDIDATE and not (user.is_staff or user.is_superuser):
            raise serializers.ValidationError({
                "job": "Only candidates have permission to apply for jobs."
            })

        # Employers cannot apply to their own job
        if job.employer == user:
            raise serializers.ValidationError({
                "job": "Employers cannot apply to their own job postings."
            })

        # Check if job is active and accepting applications
        if not job.is_active:
            raise serializers.ValidationError({
                "job": "This job listing is closed and no longer accepting applications."
            })

        if job.application_deadline and job.application_deadline < timezone.now().date():
            raise serializers.ValidationError({
                "job": "The application deadline for this job has expired."
            })

        # Prevent duplicate applications
        if Application.objects.filter(candidate=user, job=job).exists():
            raise serializers.ValidationError({
                "job": "You have already applied for this job."
            })

        # Check resume availability: either uploaded in request or present on candidate profile
        resume = attrs.get('resume')
        profile = getattr(user, 'candidate_profile', None)
        if not resume and (not profile or not profile.resume):
            raise serializers.ValidationError({
                "resume": "Please provide a resume file or upload one to your candidate profile before applying."
            })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['candidate'] = user

        # If custom resume not provided in application, inherit candidate profile's resume
        if not validated_data.get('resume'):
            profile = getattr(user, 'candidate_profile', None)
            if profile and profile.resume:
                validated_data['resume'] = profile.resume

        return super().create(validated_data)


class CandidateApplicationDetailSerializer(serializers.ModelSerializer):
    """
    Application representation for candidates (hides confidential employer notes).
    """
    job = JobNestedSerializer(read_only=True)
    resume_url = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id',
            'job',
            'resume',
            'resume_url',
            'cover_letter',
            'status',
            'applied_date',
            'updated_date',
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.STR)
    def get_resume_url(self, obj):
        request = self.context.get('request')
        if obj.resume:
            return request.build_absolute_uri(obj.resume.url) if request else obj.resume.url
        return None


class EmployerApplicationDetailSerializer(serializers.ModelSerializer):
    """
    Application representation for employers & admins (includes candidate details and internal notes).
    """
    job = JobNestedSerializer(read_only=True)
    candidate_details = CandidateNestedSerializer(source='*', read_only=True)
    resume_url = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id',
            'job',
            'candidate_details',
            'resume',
            'resume_url',
            'cover_letter',
            'status',
            'employer_notes',
            'applied_date',
            'updated_date',
        ]
        read_only_fields = ['id', 'job', 'candidate_details', 'applied_date', 'updated_date']

    @extend_schema_field(OpenApiTypes.STR)
    def get_resume_url(self, obj):
        request = self.context.get('request')
        if obj.resume:
            return request.build_absolute_uri(obj.resume.url) if request else obj.resume.url
        return None


class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for employers and admins to update application status and notes.
    """
    class Meta:
        model = Application
        fields = ['status', 'employer_notes']

    def validate_status(self, value):
        if value not in Application.Status.values:
            raise serializers.ValidationError(f"Invalid status '{value}'. Allowed: {Application.Status.values}")
        return value
