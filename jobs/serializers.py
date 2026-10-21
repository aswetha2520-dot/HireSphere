from rest_framework import serializers
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Job


class JobEmployerInfoSerializer(serializers.Serializer):
    """
    Nested serializer displaying employer company details for a job.
    """
    id = serializers.IntegerField(source='employer.id', read_only=True)
    email = serializers.EmailField(source='employer.email', read_only=True)
    company_name = serializers.CharField(read_only=True)
    company_location = serializers.CharField(read_only=True)
    website = serializers.CharField(source='company_website', read_only=True)
    logo = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_logo(self, obj):
        request = self.context.get('request')
        if hasattr(obj.employer, 'employer_profile') and obj.employer.employer_profile.company_logo:
            logo_url = obj.employer.employer_profile.company_logo.url
            return request.build_absolute_uri(logo_url) if request else logo_url
        return None


class JobListSerializer(serializers.ModelSerializer):
    """
    Compact serializer for listing jobs.
    """
    company_name = serializers.CharField(read_only=True)
    company_logo = serializers.SerializerMethodField()
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Job
        fields = [
            'id',
            'title',
            'company_name',
            'company_logo',
            'employment_type',
            'experience_level',
            'remote_status',
            'location',
            'salary_min',
            'salary_max',
            'number_of_openings',
            'application_deadline',
            'is_active',
            'is_open',
            'created_at',
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_company_logo(self, obj):
        request = self.context.get('request')
        if hasattr(obj.employer, 'employer_profile') and obj.employer.employer_profile.company_logo:
            logo_url = obj.employer.employer_profile.company_logo.url
            return request.build_absolute_uri(logo_url) if request else logo_url
        return None


class JobDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for retrieving single job postings.
    """
    employer_info = JobEmployerInfoSerializer(source='*', read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    applications_count = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id',
            'title',
            'description',
            'responsibilities',
            'required_skills',
            'qualifications',
            'employment_type',
            'experience_level',
            'remote_status',
            'location',
            'salary_min',
            'salary_max',
            'number_of_openings',
            'application_deadline',
            'is_active',
            'is_open',
            'employer_info',
            'applications_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'applications_count']

    @extend_schema_field(OpenApiTypes.INT)
    def get_applications_count(self, obj):
        request = self.context.get('request')
        # Only show applicant count to the job owner employer or admin
        if request and request.user.is_authenticated:
            if obj.employer == request.user or request.user.is_staff or request.user.is_superuser:
                return obj.applications.count()
        return None


class JobCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating job postings by Employers.
    """
    class Meta:
        model = Job
        fields = [
            'id',
            'title',
            'description',
            'responsibilities',
            'required_skills',
            'qualifications',
            'employment_type',
            'experience_level',
            'salary_min',
            'salary_max',
            'location',
            'remote_status',
            'number_of_openings',
            'application_deadline',
            'is_active',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        salary_min = attrs.get('salary_min')
        salary_max = attrs.get('salary_max')

        # Fallback to instance values on partial updates
        if salary_min is None and self.instance:
            salary_min = self.instance.salary_min
        if salary_max is None and self.instance:
            salary_max = self.instance.salary_max

        if salary_min is not None and salary_max is not None:
            if salary_min > salary_max:
                raise serializers.ValidationError({
                    'salary_min': 'Minimum salary cannot exceed maximum salary.'
                })

        deadline = attrs.get('application_deadline')
        if deadline and deadline < timezone.now().date():
            raise serializers.ValidationError({
                'application_deadline': 'Application deadline cannot be in the past.'
            })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['employer'] = user
        return super().create(validated_data)
