from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.db import transaction
from api.models import User, CompanyProfile, UserRole, Department, Client


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


class DepartmentAdminCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

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

        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone_number=validated_data["phone_number"],
            role=validated_data["role"],
            department=validated_data["department"],
            company=request_user.company,
            is_staff=True,
        )
