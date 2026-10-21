from rest_framework import permissions
from .models import User


class IsCandidate(permissions.BasePermission):
    """
    Allows access only to authenticated candidate users.
    """
    message = "Only candidates have permission to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.CANDIDATE
        )


class IsEmployer(permissions.BasePermission):
    """
    Allows access only to authenticated employer users.
    """
    message = "Only employers have permission to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.EMPLOYER
        )


class IsEmployerOrAdmin(permissions.BasePermission):
    """
    Allows access to employers or admin/staff users.
    """
    message = "Only employers or administrators have permission to perform this action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return (
            request.user.role == User.Role.EMPLOYER or
            request.user.role == User.Role.ADMIN or
            request.user.is_staff or
            request.user.is_superuser
        )


class IsAdminUserOnly(permissions.BasePermission):
    """
    Allows access only to administrators.
    """
    message = "Only administrators have permission to perform this action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return (
            request.user.role == User.Role.ADMIN or
            request.user.is_staff or
            request.user.is_superuser
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission allowing only the owner of the object or an admin to access/edit.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_staff or request.user.is_superuser or request.user.role == User.Role.ADMIN:
            return True
        owner = getattr(obj, 'user', None) or getattr(obj, 'employer', None) or getattr(obj, 'candidate', None)
        return owner == request.user
