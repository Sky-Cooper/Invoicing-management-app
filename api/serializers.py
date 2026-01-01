from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.db import transaction
from api.models import (
    User,
    CompanyProfile,
    UserRole,
    Department,
    Client,
    Chantier,
    Employee,
    ChantierAssignment,
    Attendance,
    Item,
    Invoice,
    InvoiceItem,
    Expense,
    Payment,
    EmployeeEOSB,
    EmployeeWorkingContract,
    Quote,
    QuoteItem,
    PurchaseOrder, 
    POItem
)
from django.db.models import Sum
from django.conf import settings


class CompanyOwnerRegistrationSerializer(serializers.Serializer):

    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    phone_number = serializers.CharField(required=False)
    preferred_language = serializers.CharField(required=False)

    company_name = serializers.CharField()
    company_address = serializers.CharField()
    company_phone = serializers.CharField()
    company_email = serializers.EmailField()
    ice = serializers.CharField()
    rc = serializers.CharField(required=False, allow_blank=True)
    patent = serializers.CharField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    bank_name = serializers.CharField(required=False, allow_blank=True)
    bank_account_number = serializers.CharField(required=False, allow_blank=True)
    bank_rib = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    @transaction.atomic
    def create(self, validated_data):

        company = CompanyProfile.objects.create(
            name=validated_data["company_name"],
            address=validated_data["company_address"],
            phone=validated_data["company_phone"],
            email=validated_data["company_email"],
            ice=validated_data["ice"],
            rc=validated_data.get("rc"),
            patent=validated_data.get("patent"),
            website=validated_data.get("website"),
            bank_name=validated_data.get("bank_name"),
            bank_account_number=validated_data.get("bank_account_number"),
            bank_rib=validated_data.get("bank_rib"),
        )

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone_number=validated_data.get("phone_number"),
            preferred_language=validated_data.get("preferred_language", "fr"),
            role=UserRole.COMPANY_ADMIN,
            company=company,
            is_staff=True,
        )

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["username"] = user.get_full_name()
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user

        data.update(
            {
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.get_full_name(),
                "role": user.role,
                "preferred_language": user.preferred_language,
            }
        )

        return data


class HrAdminRetrieveDataSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "role_display",
            "profile_image",
            "department",
            "department_name",
            "company",
            "company_name",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "role_display",
            "department_name",
            "company_name",
        ]


class UserDataSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "role_display",
            "preferred_language",
            "profile_image",
            "department",
            "department_name",
            "company",
            "company_name",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "role_display",
            "department_name",
            "company_name",
            "created_at",
            "updated_at",
        ]

    def update(self, instance, validated_data):

        profile_image = validated_data.pop("profile_image", None)
        if profile_image:
            instance.profile_image = profile_image

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class CompanyProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompanyProfile
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def update(self, instance, validated_data):

        request = self.context.get("request")
        user = request.user

        if user.role != UserRole.COMPANY_ADMIN:
            raise serializers.ValidationError(
                "Only company admin can access this resource"
            )

        return super().update(instance, validated_data)


class DepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["id", "created_at", "company"]

    def create(self, validated_data):
        user = self.context["request"].user

        validated_data["company"] = user.company

        return super().create(validated_data)


class DepartmentAdminRetrieveSerializer(serializers.ModelSerializer):

    department = DepartmentSerializer(read_only=True)
    company = CompanyProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "department",
            "company",
        ]


class UserNestedSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "department",
            "company",
            "preferred_language",
            "is_active",
            "password",
        ]
        extra_kwargs = {
            "email": {"required": False},
            "phone_number": {"required": False},
        }

    def validate_email(self, value):
        request = self.context.get("request")

        if self.instance:

            if User.objects.filter(email=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(
                    "User with this email already exists."
                )
        else:

            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError(
                    "User with this email already exists."
                )

        return value

    def validate_phone_number(self, value):
        if not value:
            return value

        if self.instance:

            if (
                User.objects.filter(phone_number=value)
                .exclude(id=self.instance.id)
                .exists()
            ):
                raise serializers.ValidationError(
                    "User with this phone number already exists."
                )
        else:

            if User.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError(
                    "User with this phone number already exists."
                )

        return value

    def update(self, instance, validated_data):

        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserNestedSerializer()

    class Meta:
        model = Employee
        fields = [
            "id",
            "user",
            "cin",
            "job_title",
            "hire_date",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop("user")

        request_user = self.context["request"].user

        user = User.objects.create_user(
            email=user_data["email"],
            password=user_data["password"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            phone_number=user_data.get("phone_number"),
            role=UserRole.EMPLOYEE,
            preferred_language=user_data.get("preferred_language", "fr"),
            company=request_user.company,
            is_staff=False,
        )

        employee = Employee.objects.create(
            user=user,
            **validated_data
        )

        return employee

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)

        if user_data:
            user = instance.user
            password = user_data.pop("password", None)

            for attr, value in user_data.items():
                setattr(user, attr, value)

            if password:
                user.set_password(password)

            user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class DepartmentAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "password",
            "phone_number",
            "role",
            "department",
        ]

        read_only_fields = ["id"]

    def validate_role(self, value):
        if not value in [UserRole.HR_ADMIN, UserRole.INVOICING_ADMIN]:
            raise serializers.ValidationError("invalid department admin role")

        return value

    def validate_department(self, department):
        user = self.context["request"].user
        if department.company != user.company:
            raise serializers.ValidationError(
                "this department does not belong to your company"
            )

        return department

    def create(self, validated_data):
        request_user = self.context["request"].user
        password = validated_data.pop('password')

        return User.objects.create_user(
            email=validated_data["email"],
            password=password,
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone_number=validated_data["phone_number"],
            role=validated_data["role"],
            department=validated_data["department"],
            company=request_user.company,
            is_staff=True,
        )

    def update(self, instance, validated_data):
        request_user = self.context['request'].user
        if not (request_user.is_superuser or request_user.role == UserRole.COMPANY_ADMIN):
            serializers.ValidationError("You are not allowed to update admins")

        password = validated_data.pop("password", None)

        for attr , value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)


        instance.save()

        return instance


class ClientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Client
        fields = "__all__"
        read_only_fields = ["id", "created_at", "company"]

    def create(self, validated_data):
        user = self.context["request"].user
        if not user.role == UserRole.COMPANY_ADMIN:
            raise serializers.ValidationError(
                "only super admins or company owner that can access this resource"
            )

        validated_data["company"] = user.company

        return super().create(validated_data)

class ChantierMiniSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Chantier
        fields = [
            "id",
            "name",
            "location",
            "department",
            "department_name",
            "start_date",
            "end_date",
        ]




class ChantierAssignmentSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)
    chantier = ChantierMiniSerializer(read_only = True)
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="employee",
        write_only=True,
    )
    chantier_id = serializers.PrimaryKeyRelatedField(
        queryset=Chantier.objects.all(),
        source="chantier",
        write_only=True,
    )

    class Meta:
        model = ChantierAssignment
        fields = [
            "id",
            "employee",
            "employee_id",
            "chantier",
            "chantier_id",
            "description",
            "start_date",
            "end_date",
            "is_active",
        ]

    def validate(self, attrs):
        employee = attrs.get("employee")
        chantier = attrs.get("chantier")

        if ChantierAssignment.objects.filter(
            employee=employee,
            chantier=chantier
        ).exists():
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "This employee is already assigned to this chantier."
                    ]
                }
            )

        return attrs

class ChantierSerializer(serializers.ModelSerializer):
    responsible = DepartmentAdminRetrieveSerializer(read_only=True, many=True)
    responsible_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=UserRole.HR_ADMIN),
        source="responsible",
        write_only=True,
        required=False,
        many=True
    )

    employees = ChantierAssignmentSerializer(
        source="employee_assignments", many=True, read_only=True
    )

    class Meta:
        model = Chantier
        fields = [
            "id",
            "name",
            "location",
            "description",
            "contract_number",
            "document", 
            "contract_date",
            "department",
            "client",
            "responsible",
            "responsible_ids",
            "start_date",
            "end_date",
            "employees",
            "created_at",
        ]



class AttendanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Attendance
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        user = self.context["request"].user
        chantier = attrs.get("chantier")
        employee = attrs.get("employee")
        date = attrs.get("date")
        present = attrs.get("present", False)
        hours_worked = attrs.get("hours_worked", 0)

        if not (
            user.is_superuser or
            user.role in [UserRole.HR_ADMIN, UserRole.COMPANY_ADMIN]
        ):
            raise serializers.ValidationError(
                "You are not allowed to mark attendance"
            )

       
        if user.role == UserRole.HR_ADMIN:
            if not chantier.responsible.filter(id=user.id).exists():
                raise serializers.ValidationError(
                    "You are not responsible for this chantier"
                )

      
        if user.role == UserRole.COMPANY_ADMIN:
            if chantier.department.company != user.company:
                raise serializers.ValidationError(
                    "This chantier belongs to a different company"
                )

      
        if Attendance.objects.filter(
            employee=employee,
            chantier=chantier,
            date=date
        ).exists():
            raise serializers.ValidationError(
                "Attendance already recorded for this employee on this date"
            )

     
        if not present and hours_worked > 0:
            raise serializers.ValidationError(
                "Hours worked must be 0 if employee is not present"
            )

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["employee"] = EmployeeSerializer(instance.employee).data
        data["chantier"] = ChantierSerializer(instance.chantier).data
        return data



class ItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = Item
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ExpenseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Expense
        fields = "__all__"
        read_only_fields = ["id", "created_at", "created_by"]

    
    def create(self, validated_data):
        user = self.context['request'].user
        if not user.role  in [UserRole.COMPANY_ADMIN, UserRole.INVOICING_ADMIN, UserRole.HR_ADMIN]:
            raise serializer.ValidationError("only company admin, invoicing admin , hr admin, allowed to create expenses")

        validated_data['created_by'] = user

        return super().create(validated_data)


    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["chantier"] = ChantierSerializer(instance.chantier).data
        return data


class InvoiceItemSerializer(serializers.ModelSerializer):
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), source="item", write_only=True, required=False
    )

    class Meta:
        model = InvoiceItem
        fields = [
            "id",
            "item_id",
            "item_code",
            "item_name",
            "item_description",
            "unit",
            "quantity",
            "unit_price",
            "subtotal",
            "tax_rate",
        ]
        read_only_fields = ["subtotal"]


class InvoiceSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    invoice_items = InvoiceItemSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source="client.company_name", read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = [
            "invoice_number",
            "created_by",
            "subtotal",
            "discount_amount",
            "total_ht",
            "tax_amount",
            "total_ttc",
            "amount_in_words",
            "remaining_balance"
        ]

    def validate(self, attrs):
        user = self.context["request"].user
        if attrs.get("client") and attrs["client"].company != user.company:
            raise serializers.ValidationError("Client does not belong to your company.")
        return attrs
        
    def get_download_url(self, obj):
        request = self.context.get("request")

        if not obj.invoice_number:
            return None

        filename = f"facture_{obj.invoice_number.replace('/', '_')}.pdf"

        if request:
            return request.build_absolute_uri(
                f"{settings.MEDIA_URL}invoices/{filename}"
            )

        return f"{settings.MEDIA_URL}invoices/{filename}"

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")
       

        invoice = Invoice.objects.create(**validated_data)

        total_subtotal = 0
        for item_data in items_data:

            item_obj = InvoiceItem.objects.create(invoice=invoice, **item_data)
            total_subtotal += item_obj.subtotal

        invoice.subtotal = total_subtotal
        invoice.save()

        return invoice


class InvoiceItemSerializer(serializers.ModelSerializer):
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), source="item", write_only=True, required=False
    )

    class Meta:
        model = InvoiceItem
        fields = [
            "id",
            "item_id",
            "item_code",
            "item_name",
            "item_description",
            "unit",
            "quantity",
            "unit_price",
            "subtotal",
            "tax_rate",
        ]
        read_only_fields = ["subtotal"]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = [
            "invoice_number",
            "created_by",
            "subtotal",
            "discount_amount",
            "download_url",
            "total_ht",
            "tax_amount",
            "total_ttc",
            "amount_in_words",
        ]

    def validate(self, attrs):
        user = self.context["request"].user
        if attrs.get("client") and attrs["client"].company != user.company:
            raise serializers.ValidationError("Client does not belong to your company.")
        return attrs


class PaymentSerializer(serializers.ModelSerializer):

    payment_method_display = serializers.CharField(
        source="get_payment_method_display", read_only=True
    )

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        invoice = attrs.get("invoice") or self.instance.invoice
        amount = attrs.get("amount")

        total_paid = (
            invoice.payments.exclude(pk=getattr(self.instance, "pk", None)).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        if total_paid + amount > invoice.total_ttc:
            raise serializers.ValidationError(
                {"amount": "Payment exceeds invoice total."}
            )

        return attrs



class EmployeeWorkingContractSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmployeeWorkingContract
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        user = self.context["request"].user

        if user.role not in [UserRole.COMPANY_ADMIN, UserRole.HR_ADMIN]:
            raise serializers.ValidationError(
                "Only Company Admin or HR Admin can create an employee working contract"
            )

        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["employee"] = EmployeeSerializer(instance.employee).data
        return data




class EmployeeEOSBSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmployeeEOSB
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        user = self.context["request"].user

        if user.role not in [UserRole.COMPANY_ADMIN, UserRole.HR_ADMIN]:
            raise serializers.ValidationError(
                "Only Company Admin or HR Admin can create an end of service benefit record"
            )

        employee = validated_data.get("employee")


        if hasattr(employee, "eosb_record"):
            raise serializers.ValidationError(
                "This employee already has an end of service benefit record"
            )

        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["employee"] = EmployeeSerializer(instance.employee).data
        return data



class QuoteItemSerializer(serializers.ModelSerializer):
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), source="item", write_only=True, required=False
    )
    class Meta:
        model = QuoteItem
        fields = ["id", "item_id", "item_code", "item_name", "item_description", "unit", "quantity", "unit_price", "subtotal", "tax_rate"]
        read_only_fields = ["subtotal"]

class QuoteSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True, read_only=True)
    download_url = serializers.SerializerMethodField()
    client_name = serializers.CharField(source="client.company_name", read_only=True)

    class Meta:
        model = Quote
        fields = "__all__"
        read_only_fields = ["created_by", "subtotal", "total_ht", "total_ttc", "amount_in_words", "tax_amount", "discount_amount"]

    def get_download_url(self, obj):
        if not obj.quote_number: return None
        filename = f"devis_{obj.quote_number.replace('/', '_')}.pdf"
        return f"{settings.MEDIA_URL}quotes/{filename}"

class QuoteCreateSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True) # Nested Write
    class Meta:
        model = Quote
        fields = "__all__"
        read_only_fields = ["created_by", "subtotal", "total_ht", "total_ttc", "amount_in_words"]


class POItemSerializer(serializers.ModelSerializer):
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), source="item", write_only=True, required=False
    )
    class Meta:
        model = POItem
        fields = ["id", "item_id", "item_code", "item_name", "item_description", "unit", "quantity", "unit_price", "subtotal", "tax_rate"]
        read_only_fields = ["subtotal"]

class POSerializer(serializers.ModelSerializer):
    items = POItemSerializer(many=True, read_only=True)
    download_url = serializers.SerializerMethodField()
    client_name = serializers.CharField(source="client.company_name", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = ["created_by", "subtotal", "total_ht", "total_ttc", "amount_in_words", "tax_amount", "discount_amount"]

    def get_download_url(self, obj):
        if not obj.po_number: return None
        filename = f"bc_{obj.po_number.replace('/', '_')}.pdf"
        return f"{settings.MEDIA_URL}purchase_orders/{filename}"

class POCreateSerializer(serializers.ModelSerializer):
    items = POItemSerializer(many=True)
    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = ["created_by", "subtotal", "total_ht", "total_ttc", "amount_in_words"]




class QuotePatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = ["status", "project_description", "valid_until", "chantier"]
        read_only_fields = [
            "subtotal", "total_ht", "total_ttc", "amount_in_words", "discount_amount", "tax_amount"
        ]

class POPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = ["status", "project_description", "expected_delivery_date", "chantier"]
        read_only_fields = [
            "subtotal", "total_ht", "total_ttc", "amount_in_words", "discount_amount", "tax_amount"
        ]
