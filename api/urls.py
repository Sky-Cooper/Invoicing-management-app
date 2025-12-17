from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyOwnerRegistrationView,
    UserDetailsUpdateView,
    CompanyDetailsUpdateView,
    DepartmentViewSet,
    DepartmentAdminRetrieveViewSet,
    DepartmentAdminViewSet,
    ClientViewSet,
    EmployeeViewSet,
    ChantierAssignmentViewSet,
    ChantierViewSet,
)


router = DefaultRouter()
router.register(r"departments", DepartmentViewSet, basename="departments")
router.register(
    r"departments-admins", DepartmentAdminViewSet, basename="departments-admins"
)
router.register(r"clients", ClientViewSet, basename="clients")
router.register(r"employees", EmployeeViewSet, basename="employees")
router.register(r"chantiers", ChantierViewSet, basename="chantiers")
router.register(
    r"chantiers-assignments",
    ChantierAssignmentViewSet,
    basename="chantier-assignments",
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
