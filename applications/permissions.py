from rest_framework import permissions
from accounts.models import User


class IsApplicationParticipantOrAdmin(permissions.BasePermission):
    """
    Object-level permission:
    - Candidate who submitted the application
    - Employer who posted the job
    - Staff / Superuser / Admin
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if obj.candidate == user:
            return True

        if obj.job.employer == user:
            return True

        return False


class CanUpdateApplication(permissions.BasePermission):
    """
    Object-level permission for updating an application:
    - Candidate can modify their application (e.g. withdraw or change cover letter).
    - Employer (owner of job) can update status or notes.
    - Admin has full access.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser or user.role == User.Role.ADMIN:
            return True

        if obj.candidate == user:
            return True

        if obj.job.employer == user:
            return True

        return False


class CanDeleteApplication(permissions.BasePermission):
    """
    Permission for deleting an application:
    - Candidate can delete their own application ONLY while status is PENDING.
    - Admin can delete anytime.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser or user.role == User.Role.ADMIN:
            return True

        # Candidate can delete/cancel only if still pending
        if obj.candidate == user and obj.status == obj.Status.PENDING:
            return True

        return False


class IsJobOwnerOrAdmin(permissions.BasePermission):
    """
    Permission allowing access only to the Employer who created the job or an Admin.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or user.is_superuser or user.role == User.Role.ADMIN:
            return True
        job = getattr(obj, 'job', obj)
        return getattr(job, 'employer', None) == user
