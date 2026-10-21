from rest_framework import permissions
from accounts.models import User


class IsJobEmployerOrReadOnly(permissions.BasePermission):
    """
    Custom permission for Jobs:
    - Anyone (including unauthenticated) can read (GET, HEAD, OPTIONS).
    - Only authenticated employers or admins can create (POST).
    - Only the job owner (employer who posted it) or admin can edit/delete (PUT, PATCH, DELETE).
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not (request.user and request.user.is_authenticated):
            return False
        return (
            request.user.role == User.Role.EMPLOYER or
            request.user.role == User.Role.ADMIN or
            request.user.is_staff or
            request.user.is_superuser
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # If the job is active, anyone can view it
            if obj.is_active:
                return True
            # If the job is inactive, only the owner employer or admin can view it
            if request.user and request.user.is_authenticated:
                return (
                    obj.employer == request.user or
                    request.user.is_staff or
                    request.user.is_superuser or
                    request.user.role == User.Role.ADMIN
                )
            return False

        # Modifying requires ownership or admin rights
        if not (request.user and request.user.is_authenticated):
            return False
        return (
            obj.employer == request.user or
            request.user.is_staff or
            request.user.is_superuser or
            request.user.role == User.Role.ADMIN
        )
