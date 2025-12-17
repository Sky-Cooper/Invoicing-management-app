from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyOwnerRegistrationView,
    UserDetailsUpdateView,
    CompanyDetailsUpdateView,
    DepartmentViewSet,
    DepartmentAdminRetrieveViewSet,
    DepartmentAdminViewSet,
)


router = DefaultRouter()
router.register(r"departments", DepartmentViewSet, basename="departments")
router.register(
    r"departments-admins", DepartmentAdminViewSet, basename="departments-admins"
)


urlpatterns = [
    path("register/company-owner", CompanyOwnerRegistrationView.as_view()),
    path("profile", UserDetailsUpdateView.as_view(), name="user-profile"),
    path(
        "departments/admins/me",
        DepartmentAdminRetrieveViewSet.as_view(),
        name="department-admins",
    ),
    path("company/details", CompanyDetailsUpdateView.as_view(), name="company-details"),
    path("", include(router.urls)),
]
