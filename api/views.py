from django.shortcuts import render
from .models import User, UserRole, CompanyProfile, Department
from .serializers import (
    CustomTokenObtainPairSerializer,
    CompanyOwnerRegistrationSerializer,
    UserDataSerializer,
    CompanyProfileSerializer,
    DepartmentSerializer,
    DepartmentAdminRetrieveSerializer,
    DepartmentAdminCreateSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from .permissions.roles import IsCompanyOrSuperAdmin
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied
from rest_framework import viewsets


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        data = serializer.validated_data
        response = Response(data, status=200)

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Strict",
            max_age=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
        )

        response.set_cookie(
            key="access_token",
            value=str(access),
            httponly=False,
            secure=not settings.DEBUG,
            samesite="Strict",
            max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
        )

        return response


class CookieTokenRefreshView(TokenRefreshView):

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token is None:
            return Response(
                {"detail": "Refresh token not provided"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        access_token = serializer.validated_data["access"]

        response = Response({"access": access_token}, status=status.HTTP_200_OK)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=False,
            secure=not settings.DEBUG,
            samesite="Strict",
            max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
        )

        return response


class CompanyOwnerRegistrationView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = CompanyOwnerRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "Company owner registered successfully",
                    "user_id": str(user.id),
                    "company_id": str(user.company.id),
                    "role": user.role,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Department.objects.all()

        return Department.objects.filter(company=user.company)


class UserDetailsUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CompanyDetailsUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = CompanyProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOrSuperAdmin]

    def get_object(self):
        company = self.request.user.company

        if not company:
            raise NotFound("User is not associated with any company")

        return company


class DepartmentAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsCompanyOrSuperAdmin]
    serializer_class = DepartmentAdminCreateSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return User.objects.filter(
                role__in=[UserRole.HR_ADMIN, UserRole.INVOICING_ADMIN]
            )

        if user.role == UserRole.COMPANY_ADMIN:
            return User.objects.filter(
                role__in=[UserRole.HR_ADMIN, UserRole.INVOICING_ADMIN],
                company=user.company,
            )

        return User.objects.none()


class DepartmentAdminRetrieveViewSet(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DepartmentAdminRetrieveSerializer

    def get_object(self):
        user = self.request.user

        if user.role not in [UserRole.INVOICING_ADMIN, UserRole.HR_ADMIN]:
            raise PermissionDenied("only departments admin can access this endpoint")

        return user
