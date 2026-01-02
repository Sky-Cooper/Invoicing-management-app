from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from phonenumber_field.modelfields import PhoneNumberField
import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Max


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
    PARTIALLY_PAID = "PARTIALLY_PAID", "Partially paid"


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
    company = models.ForeignKey(
        CompanyProfile, on_delete=models.SET_NULL, null=True, related_name="clients"
    )

    def __str__(self):
        return self.company_name


class Employee(models.Model):
    cin = models.CharField(max_length=50, unique=True)
    job_title = models.CharField(max_length=150)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, related_name="employee_profile"
    )
    hire_date = models.DateField(null=True, blank=True)
    is_currently_working = models.BooleanField(default = True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() if self.user else {self.id }}"







class EmployeeWorkingContract(models.Model):
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='working_contract'
    )
    contract_number = models.CharField(max_length=100, unique=True)
    contract_start_date = models.DateField()
    contract_end_date = models.DateField(null=True, blank=True)
    job_title = models.CharField(max_length=150) 
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    contract_pdf = models.FileField(
        upload_to='contracts/',
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee} - {self.contract_number}"



class EmployeeEOSB(models.Model):
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='eosb_record'
    )


    last_job_title = models.CharField(max_length=150)
    last_salary = models.DecimalField(max_digits=12, decimal_places=2)
    hire_date = models.DateField()
    exit_date = models.DateField()


    total_years_of_service = models.DecimalField(max_digits=5, decimal_places=2) 
    basic_end_of_service_payment = models.DecimalField(max_digits=12, decimal_places=2)
    bonuses_paid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    net_payment = models.DecimalField(max_digits=12, decimal_places=2)


    eosb_pdf = models.FileField(
        upload_to='eosb_statements/',
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"EOSB - {self.employee} ({self.exit_date})"



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

    employees = models.ManyToManyField(
        Employee,
        through="ChantierAssignment",
        related_name="chantiers",
    )

    responsible = models.ManyToManyField(
        User,
        blank = True,
        related_name="responsible_chantiers",
        limit_choices_to={"role": UserRole.HR_ADMIN},
    )
    document = models.FileField(
        upload_to="chantiers/",
        null=True,
        blank=True
    )

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def status(self):
     
        from django.utils import timezone

        today = timezone.now().date()

        if today < self.start_date:
            return "NOT_STARTED"
        elif self.end_date and today > self.end_date:
            return "COMPLETED"
        else:
            return "IN_PROGRESS"


class ChantierAssignment(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="chantier_assignments",
    )
    chantier = models.ForeignKey(
        Chantier, on_delete=models.CASCADE, related_name="employee_assignments"
    )
    description = models.CharField(max_length=128, blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("employee", "chantier")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} -> {self.chantier.name}"




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

    def __str__(self):
        return f"{self.employee} - {self.chantier} ({self.date})"


class Item(models.Model):
    code = models.CharField(max_length=50, blank=True, null=True)  #
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=50)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(
        CompanyProfile, on_delete=models.SET_NULL, null=True, related_name="items"
    )

    def __str__(self):
        return f"{self.code} - {self.name}" if self.code else self.name


class Invoice(models.Model):
    invoice_number = models.CharField(
    max_length=50,
    unique=True,
    blank=True
)
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
    Subject = models.CharField(max_length=255, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_ht = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_ttc = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    remaining_balance = models.DecimalField(max_digits = 14, decimal_places = 2, null = True, blank = True)
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

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.client.company_name}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)


    def generate_invoice_number(self):
        
        date = self.issued_date or timezone.now().date()
        year = date.year
        month = f"{date.month:02d}"

        prefix = f"{year}-{month}-"

        with transaction.atomic():
            last_invoice = (
                Invoice.objects
                .filter(invoice_number__startswith=prefix)
                .aggregate(max_number=Max("invoice_number"))
            )["max_number"]

            if last_invoice:
                last_seq = int(last_invoice.split("-")[-1])
                next_seq = last_seq + 1
            else:
                next_seq = 1

            return f"{prefix}{next_seq:04d}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="invoice_items"
    )
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    item_code = models.CharField(max_length=50, blank=True, null=True)
    item_name = models.CharField(max_length=255)
    item_description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        if self.item and not self.item_name:
            self.item_code = self.item.code
            self.item_name = self.item.name
            self.item_description = self.item.description
            self.unit = self.item.unit
            self.unit_price = self.item.unit_price
            self.tax_rate = self.item.tax_rate

        self.subtotal = self.quantity * self.unit_price
        self.tax_amount = self.subtotal * (self.tax_rate / Decimal("100"))
        self.total = self.subtotal + self.tax_amount

        super().save(*args, **kwargs)


class Expense(models.Model):
    chantier = models.ForeignKey(
        Chantier, on_delete=models.CASCADE, related_name="expenses"
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=ExpenseCategory.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    document = models.FileField(
    upload_to="expenses/",
    null=True,
    blank=True
)

    expense_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null = True, related_name = "expenses")


class Payment(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    payment_date = models.DateField()
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete = models.SET_NULL, null = True, blank = True, related_name = "payments")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment of {self.amount} for Invoice {self.invoice.invoice_number}"

    class Meta:
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["payment_date"]),
            models.Index(fields=["payment_method"]),
        ]



class ChatMessage(models.Model):
    message = models.TextField()
    ai_response = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_messages"
    )

    def __str__(self):
        return f"Chat by {self.sent_by.get_full_name()} at {self.created_at}"





class QuoteStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"

class POStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent"
    CONFIRMED = "CONFIRMED", "Confirmed"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class Quote(models.Model):
    quote_number = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="quotes")
    chantier = models.ForeignKey(Chantier, on_delete=models.SET_NULL, null=True, blank=True, related_name="quotes")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_quotes")
    
    status = models.CharField(max_length=20, choices=QuoteStatus.choices, default=QuoteStatus.DRAFT)
    

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_ht = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_ttc = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_in_words = models.TextField(blank=True, null=True)

    issued_date = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    project_description = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Devis {self.quote_number}"

class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    item_code = models.CharField(max_length=50, blank=True, null=True)
    item_name = models.CharField(max_length=255)
    item_description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
     
        if self.item and not self.item_name:
            self.item_code = self.item.code
            self.item_name = self.item.name
            self.item_description = self.item.description
            self.unit = self.item.unit
            self.unit_price = self.item.unit_price
            self.tax_rate = self.item.tax_rate
            
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class PurchaseOrder(models.Model):
    po_number = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="purchase_orders")
    chantier = models.ForeignKey(Chantier, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_orders")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_pos")
    
    status = models.CharField(max_length=20, choices=POStatus.choices, default=POStatus.DRAFT)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_ht = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_ttc = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_in_words = models.TextField(blank=True, null=True)

    issued_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    project_description = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"BC {self.po_number}"

class POItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    item_code = models.CharField(max_length=50, blank=True, null=True)
    item_name = models.CharField(max_length=255)
    item_description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if self.item and not self.item_name:
            self.item_code = self.item.code
            self.item_name = self.item.name
            self.item_description = self.item.description
            self.unit = self.item.unit
            self.unit_price = self.item.unit_price
            self.tax_rate = self.item.tax_rate
            
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)