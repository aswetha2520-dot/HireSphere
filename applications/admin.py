from django.contrib import admin
from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate', 'job', 'status', 'applied_date', 'updated_date')
    list_filter = ('status', 'applied_date')
    search_fields = ('candidate__email', 'job__title', 'job__employer__email')
    raw_id_fields = ('candidate', 'job')
    readonly_fields = ('applied_date', 'updated_date')
