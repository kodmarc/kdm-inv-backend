from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinLengthValidator
from django.db import transaction
from organizations.models import Organization, Branch

User = get_user_model()

class SignupSerializer(serializers.Serializer):
    org_id = serializers.CharField(
        max_length=50,
        validators=[
            MinLengthValidator(5, message='Organization ID must be at least 5 characters long.'),
            RegexValidator(
                regex=r'^[a-zA-Z0-9]+$',
                message='Organization ID must contain only letters and numbers without special characters.'
            ),
            RegexValidator(
                regex=r'[a-zA-Z]',
                message='Organization ID must contain at least one letter.'
            ),
            RegexValidator(
                regex=r'[0-9]',
                message='Organization ID must contain at least one number.'
            ),
        ]
    )
    org_name = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_org_id(self, value):
        val = value.lower().strip()
        if Organization.objects.filter(org_id=val).exists():
            raise serializers.ValidationError("An organization with this ID already exists.")
        return val

    def validate_username(self, value):
        # Username must be unique globally for platform superadmins, or checked conditionally.
        # But here on signup, it's a new organization, so we just check standard unique constraints.
        val = value.strip()
        return val

    def create(self, validated_data):
        org_id = validated_data['org_id']
        org_name = validated_data['org_name']
        username = validated_data['username']
        password = validated_data['password']

        with transaction.atomic():
            # Create the Organization
            org = Organization.objects.create(
                org_id=org_id,
                name=org_name
            )
            # Create the Organization Admin User
            user = User.objects.create_superuser(
                username=username,
                password=password,
                organization=org,
                role=User.Role.ORG_ADMIN
            )
            return user


class LoginOrgSerializer(serializers.Serializer):
    org_id = serializers.CharField(max_length=50)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[User.Role.ORG_ADMIN, User.Role.ORG_USER])


class LoginBranchSerializer(serializers.Serializer):
    org_id = serializers.CharField(max_length=50)
    branch_slug = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[User.Role.BRANCH_ADMIN, User.Role.USER, User.Role.KPO])


class UserManageSerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'branch', 'is_active', 'password']
        read_only_fields = ['id']
        validators = []  # Disable default model unique validators to prevent branch from being made required

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically scope the branch queryset to the current user's organization
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            # Filter branch dropdown to only the active organization's branches
            self.fields['branch'].queryset = Branch.objects.filter(
                organization=request.user.organization
            )

    def validate(self, attrs):
        role = attrs.get('role', self.instance.role if self.instance else None)
        branch = attrs.get('branch', self.instance.branch if self.instance else None)

        if role in [User.Role.BRANCH_ADMIN, User.Role.USER, User.Role.KPO]:
            if not branch:
                raise serializers.ValidationError({"branch": "Branch is required for branch-level roles."})
        elif role in [User.Role.ORG_ADMIN, User.Role.ORG_USER]:
            # HQ users should not be bound to a single branch
            attrs['branch'] = None

        # Scope validation based on the creating user's permissions
        request = self.context.get('request')
        if request and request.user:
            creator = request.user
            if creator.role == User.Role.BRANCH_ADMIN:
                # Branch admins can only assign users to their own branch
                if branch != creator.branch:
                    raise serializers.ValidationError({"branch": "Branch Admins can only manage users in their own branch."})
                # Branch admins cannot create HQ roles
                if role in [User.Role.ORG_ADMIN, User.Role.ORG_USER]:
                    raise serializers.ValidationError({"role": "Branch Admins cannot manage Organization HQ roles."})

        # Scoped username uniqueness validation to prevent IntegrityError on database level
        username = attrs.get('username', self.instance.username if self.instance else None)
        if username:
            username = username.strip()
            organization = request.user.organization if request else None
            
            qs = User.objects.filter(organization=organization, username=username)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
                
            if role in [User.Role.ORG_ADMIN, User.Role.ORG_USER]:
                # HQ username check within organization
                if qs.filter(role__in=[User.Role.ORG_ADMIN, User.Role.ORG_USER]).exists():
                    raise serializers.ValidationError({"username": "This username is already taken by an HQ user in this organization."})
            else:
                # Branch username check within branch
                if branch and qs.filter(branch=branch, role__in=[User.Role.BRANCH_ADMIN, User.Role.USER, User.Role.KPO]).exists():
                    raise serializers.ValidationError({"username": f"This username is already taken in this branch ({branch.name})."})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        request = self.context.get('request')
        organization = request.user.organization if request else None

        user = User(**validated_data)
        if organization:
            user.organization = organization
            
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
            
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
            
        return super().update(instance, validated_data)

