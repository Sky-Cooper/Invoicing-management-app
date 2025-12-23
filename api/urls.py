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
    AttendanceViewSet,
    ItemViewSet,
    ExpenseViewSet,
    InvoiceCreateApiView,
    PaymentViewSet,
    DashboardAnalyticsView,
    ExecutiveDashboardView,
    AdvancedDashboardView,
    OpenAiViewSet,
    HrAdminRetreiveDataViewSet,

)


router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payments")
router.register(r"departments", DepartmentViewSet, basename="departments")
router.register(
    r"departments-admins", DepartmentAdminViewSet, basename="departments-admins"
)
router.register(r"items", ItemViewSet, basename="items")
router.register(r"clients", ClientViewSet, basename="clients")
router.register(r"employees", EmployeeViewSet, basename="employees")
router.register(r"chantiers", ChantierViewSet, basename="chantiers")
router.register(
    r"chantiers-assignments",
    ChantierAssignmentViewSet,
    basename="chantier-assignments",
)
router.register(r"attendances", AttendanceViewSet, basename="attendances")
router.register(r"expenses", ExpenseViewSet, basename="expenses")

urlpatterns = [
    path("register/company-owner", CompanyOwnerRegistrationView.as_view()),
    path("invoices", InvoiceCreateApiView.as_view()),
    path("invoices/<int:pk>/", InvoiceCreateApiView.as_view(), name="invoice-detail"),
    path("dashboard/data", DashboardAnalyticsView.as_view()),
    path("dashboard/executive", ExecutiveDashboardView.as_view()),
    path("dashboard/advanced", AdvancedDashboardView.as_view()),
    path("chat-ai", OpenAiViewSet.as_view()),
    path("profile", UserDetailsUpdateView.as_view(), name="user-profile"),
    path(
        "departments/admins/me",
        DepartmentAdminRetrieveViewSet.as_view(),
        name="department-admins",
    ),
    path("hr-deparements/admins", HrAdminRetreiveDataViewSet.as_view(), name="hr-deparements-admins"),
    path("company/details", CompanyDetailsUpdateView.as_view(), name="company-details"),
    path("", include(router.urls)),
]
