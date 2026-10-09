from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Allows access only to logged-in, active users whose role is ADMIN."""

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == user.Role.ADMIN
        )