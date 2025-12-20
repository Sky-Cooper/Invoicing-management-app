from rest_framework.permissions import BasePermission
from api.models import UserRole


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == UserRole.SUPER_ADMIN


class IsCompanyAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.role == UserRole.COMPANY_ADMIN
            and request.user.company is not None
        )


class IsHRAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.role == UserRole.HR_ADMIN and request.user.company is not None
        )


class IsInvoicingAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.role == UserRole.INVOICING_ADMIN
            and request.user.company is not None
        )


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.role == UserRole.EMPLOYEE and request.user.company is not None
        )


class IsCompanyOrHRAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in {
            UserRole.COMPANY_ADMIN,
            UserRole.HR_ADMIN,
        }


class CanManageInvoices(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_superuser or request.user.role in {
            UserRole.SUPER_ADMIN,
            UserRole.COMPANY_ADMIN,
            UserRole.INVOICING_ADMIN,
        }


class IsCompanyOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        allowed_roles = [UserRole.COMPANY_ADMIN]
        return request.user.role in allowed_roles
