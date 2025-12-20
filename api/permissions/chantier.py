from rest_framework.permissions import BasePermission
from api.models import UserRole


class IsChantierResponsible(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.role == UserRole.HR_ADMIN and obj.responsible == request.user
        )
