from django.shortcuts import render
from .models import (
    User,
    UserRole,
    CompanyProfile,
    Department,
    Client,
    Employee,
    Chantier,
    ChantierAssignment,
    Attendance,
    Invoice,
    Item,
    InvoiceItem,
    Expense,
)
from .serializers import (
    CustomTokenObtainPairSerializer,
    CompanyOwnerRegistrationSerializer,
    UserDataSerializer,
    CompanyProfileSerializer,
    DepartmentSerializer,
    DepartmentAdminRetrieveSerializer,
    DepartmentAdminCreateSerializer,
    ClientSerializer,
    EmployeeSerializer,
    ChantierAssignmentSerializer,
    ChantierSerializer,
    AttendanceSerializer,
    ItemSerializer,
    ExpenseSerializer,
    InvoiceItemSerializer,
    InvoiceSerializer,
    InvoiceCreateSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from .permissions.roles import (
    IsCompanyOrSuperAdmin,
    IsCompanyOrHRAdmin,
    CanManageInvoices,
)
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.template.loader import render_to_string
from django.http import HttpResponse

import tempfile
from django.db import transaction
from num2words import num2words
from .tasks import generate_invoice_pdf_task
from .services import InvoiceCalculator


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


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Client.objects.all()

        if user.role == UserRole.COMPANY_ADMIN:
            return Client.objects.filter(company=user.company)

        return Client.objects.none()

    def perform_update(self, serializer):
        client = self.get_object()
        user = self.request.user

        if not user.is_superuser and use.role != UserRole.COMPANY_ADMIN:
            raise PermissionDenied(
                "only super admins or company admins that can modify clients"
            )

        if user.company != client.company:
            raise PermissionDenied(
                "You cannot modify this client because they dont belong to your company"
            )

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if not user.is_superuser and user.role != UserRole.COMPANY_ADMIN:
            raise PermissionDenied(
                "only super admins or company admins that can delete clients"
            )

        if user.company != instance.company:
            raise PermissionDenied(
                "you cannot delete this client because they dont belong to your company"
            )

        instance.delete()


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Employee.objects.all()

        if user.role == UserRole.COMPANY_ADMIN:
            return Employee.objects.filter(user__company=user.company)

        return Employee.objects.none()

    def perform_destroy(self, instance):
        request_user = self.request.user
        if (
            not request_user.is_superuser
            and request_user.role != UserRole.COMPANY_ADMIN
        ):
            raise PermissionDenied(
                "only super admins and company admins can access this resource"
            )

        user = instance.user
        instance.delete()
        user.delete()


class ChantierViewSet(viewsets.ModelViewSet):
    serializer_class = ChantierSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user

        qs = Chantier.objects.select_related(
            "department", "client", "responsible"
        ).prefetch_related("employee_assignments__employee__user")

        if user.is_superuser:
            return qs

        if user.role in [UserRole.COMPANY_ADMIN, UserRole.HR_ADMIN]:
            return qs.filter(department__company=user.company)

        if user.role == UserRole.EMPLOYEE:
            return qs.filter(employee_assignments__employee__user=user).distinct()

        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user

        if user.role not in [UserRole.COMPANY_ADMIN, UserRole.HR_ADMIN]:
            raise PermissionDenied("Only admins can create chantiers")

        serializer.save()


class ChantierAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = ChantierAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user

        qs = ChantierAssignment.objects.select_related(
            "employee__user", "chantier", "chantier__department"
        )

        if user.is_superuser:
            return qs

        if user.role in [UserRole.COMPANY_ADMIN, UserRole.HR_ADMIN]:
            return qs.filter(chantier__department__company=user.company)

        if user.role == UserRole.EMPLOYEE:
            return qs.filter(employee__user=user)

        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user

        if user.role not in [UserRole.COMPANY_ADMIN, UserRole.HR_ADMIN]:
            raise PermissionDenied("Only admins can assign employees")

        serializer.save()


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOrHRAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            queryset = Attendance.objects.all()

        elif user.role == UserRole.COMPANY_ADMIN:
            queryset = Attendance.objects.filter(employee__user__company=user.company)

        elif user.role == UserRole.HR_ADMIN:
            queryset = Attendance.objects.filter(chantier__responsible=user)

        else:
            return Attendance.objects.none()

        date_param = self.request.query_params.get("date")

        if date_param:
            queryset = queryset.filter(date=date_param)

        return queryset


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageInvoices]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Item.objects.all()

        if user.role in [UserRole.COMPANY_ADMIN, UserRole.INVOICING_ADMIN]:
            return Item.objects.filter(company=user.company)

        return Item.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(company=user.company)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageInvoices]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Expense.objects.all()

        if user.role in [UserRole.COMPANY_ADMIN, UserRole.INVOICING_ADMIN]:
            return Expense.objects.filter(chantier__department__company=user.company)

        return Expense.objects.none()

    def perform_create(self, serializer):
        serializer.save()


class InvoiceCreateApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, CanManageInvoices]

    @transaction.atomic
    def post(self, request):
        serializer = InvoiceCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        # 1. Save Basic Invoice Data
        items_data = serializer.validated_data.pop("items")
        invoice = serializer.save(created_by=request.user)

        # 2. Create Invoice Items
        # This allows the task to access items via invoice.invoice_items.all()
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)

        # 3. Trigger Async Task after DB commit
        # We pass only the ID to keep the task payload light
        transaction.on_commit(lambda: generate_invoice_pdf_task.delay(invoice.id))

        # 4. Prepare Response
        # Note: At this exact moment, the PDF might still be generating,
        # so we return the object data immediately.
        data = InvoiceSerializer(invoice).data

        # Provide a predictable URL where the file will eventually be
        pdf_filename = f"facture_{invoice.invoice_number.replace('/', '_')}.pdf"
        data["download_url"] = request.build_absolute_uri(
            f"{settings.MEDIA_URL}invoices/{pdf_filename}"
        )

        return Response(data, status=status.HTTP_201_CREATED)
