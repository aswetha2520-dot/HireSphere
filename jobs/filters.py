import django_filters
from .models import Job


class JobFilter(django_filters.FilterSet):
    """
    FilterSet for Job listings.
    """
    title = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.CharFilter(lookup_expr='icontains')
    company = django_filters.CharFilter(
        field_name='employer__employer_profile__company_name',
        lookup_expr='icontains'
    )
    min_salary = django_filters.NumberFilter(
        field_name='salary_min',
        lookup_expr='gte'
    )
    max_salary = django_filters.NumberFilter(
        field_name='salary_max',
        lookup_expr='lte'
    )
    employment_type = django_filters.ChoiceFilter(
        choices=Job.EmploymentType.choices
    )
    experience_level = django_filters.ChoiceFilter(
        choices=Job.ExperienceLevel.choices
    )
    remote_status = django_filters.ChoiceFilter(
        choices=Job.RemoteStatus.choices
    )
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = Job
        fields = [
            'employment_type',
            'experience_level',
            'remote_status',
            'location',
            'is_active',
            'min_salary',
            'max_salary',
            'company',
            'title',
        ]
