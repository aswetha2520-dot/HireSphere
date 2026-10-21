from django.contrib import admin
from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'company_name',
        'employment_type',
        'experience_level',
        'location',
        'is_active',
        'application_deadline',
        'created_at',
    )
    list_filter = ('is_active', 'employment_type', 'experience_level', 'remote_status')
    search_fields = ('title', 'description', 'location', 'required_skills', 'employer__email')
    raw_id_fields = ('employer',)
    readonly_fields = ('created_at', 'updated_at')
