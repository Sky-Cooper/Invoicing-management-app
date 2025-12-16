from rest_framework.permissions import BasePermission


class IsSameCompany(BasePermission):
    """
    Object-level permission.
    Ensures user only accesses objects belonging to their company.
    """

    def has_object_permission(self, request, view, obj):
        return hasattr(obj, "company") and obj.company == request.user.company
