from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import (
    User,
    Department,
    CompanyProfile,
    Client,
    Chantier,
    Employee,
    Attendance,
    Item,
    Invoice,
    InvoiceItem,
    Expense,
    Payment,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "department",
        "company",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "department", "company", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("created_at", "updated_at", "last_login")

    fieldsets = (
        ("Identity", {"fields": ("email", "password")}),
        (
            "Personal Info",
            {"fields": ("first_name", "last_name", "phone_number", "profile_image")},
        ),
        ("Company Info", {"fields": ("role", "department", "company")}),
        ("Preferences", {"fields": ("preferred_language",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "company",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "ice", "rc", "patent")
    search_fields = ("name", "ice", "email")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Company Info", {"fields": ("name", "logo", "address", "website")}),
        ("Legal", {"fields": ("ice", "rc", "patent")}),
        ("Banking", {"fields": ("bank_name", "bank_account_number", "bank_rib")}),
        ("Contact", {"fields": ("email", "phone")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name",)
    readonly_fields = ("created_at",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("company_name", "contact_name", "phone", "ice")
    search_fields = ("company_name", "contact_name", "ice", "email")


@admin.register(Chantier)
class ChantierAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "client",
        "responsible",
        "start_date",
        "end_date",
    )
    list_filter = ("department", "start_date")
    search_fields = ("name", "location", "contract_number")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "cin",
        "job_title",
        "assigned_chantiers",
    )
    search_fields = (
        "cin",
        "user__first_name",
        "user__last_name",
        "user__email",
    )

    def first_name(self, obj):
        return obj.user.first_name

    first_name.admin_order_field = "user__first_name"

    def last_name(self, obj):
        return obj.user.last_name

    last_name.admin_order_field = "user__last_name"

    def assigned_chantiers(self, obj):
        return ", ".join(
            ca.chantier.name
            for ca in obj.chantier_assignments.filter(is_active=True)
        )

    assigned_chantiers.short_description = "Assigned Chantiers"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "chantier", "date", "present", "hours_worked")
    list_filter = ("date", "present", "chantier")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit", "unit_price", "tax_rate")
    search_fields = ("code", "name")


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    autocomplete_fields = ("item",)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "client",
        "status",
        "total_ttc",
        "issued_date",
        "due_date",
    )
    list_filter = ("status", "issued_date")
    search_fields = ("invoice_number", "client__company_name")
    readonly_fields = (
        "subtotal",
        "discount_amount",
        "total_ht",
        "tax_amount",
        "total_ttc",
        "created_at",
        "updated_at",
    )

    inlines = [InvoiceItemInline, PaymentInline]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("title", "chantier", "category", "amount", "expense_date")
    list_filter = ("category", "expense_date")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "payment_method", "payment_date")
    list_filter = ("payment_method", "payment_date")
