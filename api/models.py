from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from phonenumber_field.modelfields import PhoneNumberField
import uuid


class LanguageChoices(models.TextChoices):
    ARABIC = "ar", "Arabic"
    FRENCH = "fr", "French"
    ENGLISH = "en", "English"


class UserRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    COMPANY_ADMIN = "COMPANY_ADMIN", "Company Admin"
    INVOICING_ADMIN = "INVOICING_ADMIN", "Invoicing Admin"
    HR_ADMIN = "HR_ADMIN", "HR Admin"
    EMPLOYEE = "EMPLOYEE", "Employee"


class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    COMPLETED = "COMPLETED", "Completed"
    PAID = "PAID", "Paid"


class ExpenseCategory(models.TextChoices):
    MATERIAL = "MATERIAL", "Material"
    TRANSPORT = "TRANSPORT", "Transport"
    LABOR = "LABOR", "Labor"
    OTHER = "OTHER", "Other"


class PaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
    CHECK = "CHECK", "Check"
    CREDIT_CARD = "CREDIT_CARD", "Credit Card"


class ApplicationUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class CompanyProfile(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone = PhoneNumberField(region="MA")
    email = models.EmailField()
    ice = models.CharField(max_length=20, verbose_name="ICE")
    rc = models.CharField(
        max_length=50, verbose_name="Registre de Commerce", blank=True, null=True
    )
    patent = models.CharField(max_length=50, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    bank_account_number = models.CharField(max_length=100, blank=True, null=True)
    bank_rib = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to="company/")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(
        CompanyProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name="departments",
    )

    class Meta:
        unique_together = ("company", "name")

    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField(region="MA", unique=True, null=True, blank=True)
    role = models.CharField(max_length=30, choices=UserRole.choices)

    preferred_language = models.CharField(
        max_length=10, choices=LanguageChoices.choices, default=LanguageChoices.FRENCH
    )

    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, null=True, blank=True
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = ApplicationUserManager()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.get_full_name()} {self.role})"


class Client(models.Model):
    company_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    ice = models.CharField(max_length=20, verbose_name="ICE")
    rc = models.CharField(
        max_length=50, verbose_name="Registre de Commerce", blank=True, null=True
    )
    tax_id = models.CharField(
        max_length=50, verbose_name="Identifiant Fiscal", blank=True, null=True
    )
    phone = PhoneNumberField(region="MA")
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Chantier(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    contract_number = models.CharField(max_length=100, blank=True, null=True)
    contract_date = models.DateField(blank=True, null=True)

    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chantiers",
    )

    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, related_name="chantiers"
    )

    responsible = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="responsible_chantiers",
        limit_choices_to={"role": UserRole.HR_ADMIN},
    )

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    cin = models.CharField(max_length=50, unique=True)
    job_title = models.CharField(max_length=150)

    assigned_chantier = models.ForeignKey(
        Chantier, on_delete=models.SET_NULL, null=True, related_name="employees"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Attendance(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="attendances"
    )
    chantier = models.ForeignKey(
        Chantier, on_delete=models.CASCADE, related_name="attendances"
    )
    date = models.DateField()
    present = models.BooleanField(default=False)
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("employee", "chantier", "date")


class Item(models.Model):
    code = models.CharField(max_length=50, blank=True, null=True)  # For "Poste" in PDF
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=50)  # UN in PDF (M², ML, etc.)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}" if self.code else self.name


class Invoice(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True)  # Format: 006/2025
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="invoices"
    )
    chantier = models.ForeignKey(
        Chantier, on_delete=models.SET_NULL, null=True, related_name="invoices"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="invoices"
    )

    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT
    )

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_ht = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_ttc = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    amount_in_words = models.TextField(blank=True, null=True)

    issued_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, blank=True, null=True
    )
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)

    project_description = models.TextField(blank=True, null=True)
    contract_number = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["invoice_number"]),
        ]

    def save(self, *args, **kwargs):

        if not self.total_ht and self.subtotal and self.discount_percentage:
            self.discount_amount = (self.subtotal * self.discount_percentage) / 100
            self.total_ht = self.subtotal - self.discount_amount

        if self.total_ht and self.tax_rate:
            tax_decimal = int(self.tax_rate) / 100
            self.tax_amount = self.total_ht * tax_decimal
            self.total_ttc = self.total_ht + self.tax_amount

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.client.company_name}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)

    item_code = models.CharField(max_length=50, blank=True, null=True)
    item_name = models.CharField(max_length=255)
    item_description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ["item_code"]

    def save(self, *args, **kwargs):

        if not self.subtotal and self.quantity and self.unit_price:
            self.subtotal = self.quantity * self.unit_price

        if self.item and not self.item_name:
            self.item_name = self.item.name
            self.item_code = self.item.code
            self.item_description = self.item.description
            self.unit = self.item.unit
            self.unit_price = self.item.unit_price
            self.tax_rate = self.item.tax_rate

        super().save(*args, **kwargs)


class Expense(models.Model):
    chantier = models.ForeignKey(
        Chantier, on_delete=models.CASCADE, related_name="expenses"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="expenses"
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=ExpenseCategory.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    expense_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    payment_date = models.DateField()
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment of {self.amount} for Invoice {self.invoice.invoice_number}"
