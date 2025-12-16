from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyOwnerRegistrationView,
    UserDetailsUpdateView,
    CompanyDetailsUpdateView,
)


router = DefaultRouter()


urlpatterns = [
    path("register/company-owner/", CompanyOwnerRegistrationView.as_view()),
    path("profile/", UserDetailsUpdateView.as_view(), name="user-profile"),
    path(
        "company/details/", CompanyDetailsUpdateView.as_view(), name="company-details"
    ),
]
