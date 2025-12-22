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
    Payment,
    InvoiceStatus,
    ChatMessage,
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
    PaymentSerializer,
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
from .tasks import generate_invoice_pdf_task, send_thanking_invoice_task
from .services import InvoiceCalculator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .analytics.financials import FinancialAnalytics
from .permissions.roles import IsCompanyOrSuperAdmin

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .analytics.financials import FinancialAnalytics
from .analytics.advanced import AdvancedAnalytics
from .permissions.roles import IsCompanyOrSuperAdmin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .analytics.aging import AgingAnalytics
from .analytics.labor import LaborAnalytics
from .analytics.tax import TaxAnalytics
from .permissions.roles import IsCompanyOrSuperAdmin
from timezone.utils import timezone
import openai


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

        try:
            token_obj = RefreshToken(refresh_token)
            user_id = token_obj["user_id"]
            user = User.objects.get(id=user_id)

        except Exception:
            return Response(
                {"detail": "Invalid refresh Token"}, status=status.HTTP_401_UNAUTHORIZED
            )

        data = {"access_token": access_token, "role": user.role}

        response = Response(data, status=status.HTTP_200_OK)
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

        if not user.is_superuser and user.role != UserRole.COMPANY_ADMIN:
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


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageInvoices]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Payment.objects.all()

        if user.role in [UserRole.COMPANY_ADMIN, UserRole.INVOICING_ADMIN]:
            return Payment.objects.filter(invoice__client__company=user.company)

        return Payment.objects.none()


class InvoiceCreateApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, CanManageInvoices]

    @transaction.atomic
    def post(self, request):
        serializer = InvoiceCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        items_data = serializer.validated_data.pop("items")
        invoice = serializer.save(created_by=request.user)

        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)

        transaction.on_commit(lambda: generate_invoice_pdf_task.delay(invoice.id))
        data = InvoiceSerializer(invoice).data

        pdf_filename = f"facture_{invoice.invoice_number.replace('/', '_')}.pdf"
        data["download_url"] = request.build_absolute_uri(
            f"{settings.MEDIA_URL}invoices/{pdf_filename}"
        )

        return Response(data, status=status.HTTP_201_CREATED)

    def get(self, request):
        user = request.user

        if user.is_superuser:
            queryset = Invoice.objects.all()
        elif user.role in [UserRole.COMPANY_ADMIN, UserRole.INVOICING_ADMIN]:
            queryset = Invoice.objects.filter(created_by__company=user.company)
        else:
            return Response([], status=status.HTTP_200_OK)

        created_by_id = request.query_params.get("created_by")
        status_param = request.query_params.get("status")
        issued_date = request.query_params.get("issued_date")
        due_date = request.query_params.get("due_date")
        payment_date = request.query_params.get("payment_date")
        created_at = request.query_params.get("created_at")

        if created_by_id:
            queryset = queryset.filter(created_by_id=created_by_id)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if issued_date:
            queryset = queryset.filter(issued_date=issued_date)
        if due_date:
            queryset = queryset.filter(due_date=due_date)
        if payment_date:
            queryset = queryset.filter(payment_date=payment_date)
        if created_at:

            queryset = queryset.filter(created_at__date=created_at)

        queryset = queryset.select_related("client", "created_by").prefetch_related(
            "invoice_items"
        )

        serializer = InvoiceSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def patch(self, request, pk=None):
        try:
            invoice = Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist:
            return Response(
                {"error": "Invoice not found"}, status=status.HTTP_404_NOT_FOUND
            )

        old_status = invoice.status

        serializer = InvoiceSerializer(
            invoice, data=request.data, partial=True, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        updated_invoice = serializer.save()

        if (
            old_status != InvoiceStatus.PAID
            and updated_invoice.status == InvoiceStatus.PAID
        ):
            transaction.on_commit(
                lambda: send_thanking_invoice_task.delay(updated_invoice.id)
            )

        return Response(serializer.data)


class DashboardAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCompanyOrSuperAdmin]

    def get(self, request):
        company = request.user.company
        if not company:
            return Response({"error": "No company associated"}, status=400)

        analytics = FinancialAnalytics(company)

        data = {
            "summary": analytics.get_kpi_summary(),
            "revenue_trend": analytics.get_revenue_growth(),
            "expense_by_category": analytics.get_expense_breakdown(),
            "project_performance": analytics.get_chantier_profitability(),
        }

        return Response(data)


class ExecutiveDashboardView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsCompanyOrSuperAdmin]

    def get(self, request):
        company = request.user.company
        basic_stats = FinancialAnalytics(company)
        adv_stats = AdvancedAnalytics(company)

        response_data = {
            "kpis": basic_stats.get_kpi_summary(),
            "cash_flow": {
                "revenue_trend": basic_stats.get_revenue_growth(),
                "aging_report": adv_stats.get_accounts_receivable_aging(),
            },
            "market_share": {
                "top_clients": adv_stats.get_client_concentration(),
                "expense_distribution": basic_stats.get_expense_breakdown(),
            },
            "project_health": basic_stats.get_chantier_profitability(),
            "tax_compliance": adv_stats.get_tax_summary(),
        }

        return Response(response_data)


class AdvancedDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCompanyOrSuperAdmin]

    def get(self, request):
        company = request.user.company
        if not company:
            return Response({"error": "No company"}, status=400)

        aging = AgingAnalytics(company)
        labor = LaborAnalytics(company)
        tax = TaxAnalytics(company)

        return Response(
            {
                "cash_flow_health": {
                    "aging_report": aging.get_ar_aging_buckets(),
                    "dso_days": aging.calculate_dso(),
                },
                "workforce_productivity": {
                    "labor_metrics": labor.get_labor_intensity(),
                    "project_efficiency": labor.get_project_efficiency(),
                },
                "tax_planning": tax.get_tva_forecast(),
            }
        )




# Initialize OpenAI Client
client = openai.OpenAI(api_key=settings.OPENAI_KEY)


class OpenAiViewSet(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_message = request.data.get("message")

        if not user_message:
            return Response(
                {"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Daily Limit Check (10 messages per day)
        today = timezone.now().date()
        messages_sent_today = ChatMessage.objects.filter(
            sent_by=request.user, 
            created_at__date=today
        ).count()

        if messages_sent_today >= 10:
            return Response(
                {"error": "Daily limit reached. You can send 10 messages per day."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        try:
            # 2. Expert Financial Prompt Engineering
            # We explicitly define the role and set boundaries for the AI.
            system_prompt = (
                "You are an expert financial consultant, accountant, and invoicing specialist "
                "for the 'FatouraLik' platform. Your goal is to help Moroccan business owners "
                "with accounting, e-invoicing (including 2026 Moroccan laws), and financial management. "
                "STRICT RULE: Only answer questions related to finance, accounting, or business management. "
                "If a user asks about anything else (e.g., cooking, sports, general chat), politely refuse "
                "and remind them that you are a financial assistant."
            )

            # 3. Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Recommended: "gpt-4o" for better expert reasoning
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=500,
            )

            ai_content = response.choices[0].message.content

            # 4. Save to Database
            # Note: I used 'message' to match your ChatMessage model field name
            chat_obj = ChatMessage.objects.create(
                sent_by=request.user, 
                message=user_message, 
                ai_response=ai_content  # Ensure you added this field to your model!
            )

            return Response(
                {
                    "id": chat_obj.id,
                    "user_query": user_message,
                    "ai_response": ai_content,
                    "messages_remaining": 10 - (messages_sent_today + 1),
                    "created_at": chat_obj.created_at,
                },
                status=status.HTTP_200_OK,
            )

        except openai.OpenAIError as e:
            return Response(
                {"error": f"OpenAI Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )