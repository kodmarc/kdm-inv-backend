from django.db import transaction
from rest_framework import serializers
from organizations.models import Branch
from organizations.exceptions import ConflictException
from .models import Company

class CompanySerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )

    code = serializers.CharField(required=False, allow_blank=True)
    version = serializers.IntegerField(required=False)

    class Meta:
        model = Company
        fields = ['id', 'name', 'code', 'branch', 'version', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        validators = []  # Disable default unique validators to prevent fields from being made required

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically scope the branch options to the authenticated user's organization
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            self.fields['branch'].queryset = Branch.objects.filter(
                organization=request.user.organization
            )

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        user = request.user
        org = user.organization
        policy = org.company_creation_policy

        name = attrs.get('name', self.instance.name if self.instance else None)
        code = attrs.get('code', self.instance.code if self.instance else None)
        branch = attrs.get('branch', self.instance.branch if self.instance else None)

        # Enforce Policy Rules for Writes (Create/Update)
        if policy == 'ORG_ADMIN':
            # Centralized Mode
            if user.role not in ['ORG_ADMIN', 'ORG_USER']:
                raise serializers.ValidationError("Only HQ administrators can create or modify companies under Centralized policy.")
            if not self.instance:
                attrs['branch'] = None
                branch = None
        else:
            # Decentralized Mode
            if user.role not in ['BRANCH_ADMIN', 'USER']:
                raise serializers.ValidationError("HQ administrators cannot create or modify branch-level companies under Decentralized policy.")
            if not user.branch:
                raise serializers.ValidationError("You must be linked to a branch to create or modify companies under Decentralized policy.")
            if not self.instance:
                attrs['branch'] = user.branch
                branch = user.branch
            else:
                if 'branch' in attrs and attrs['branch'] != self.instance.branch:
                    raise serializers.ValidationError({"branch": "Company branch mapping cannot be changed after creation."})

        # Strip strings
        if name:
            attrs['name'] = name.strip()
        if code:
            attrs['code'] = code.strip()

        # Check unique constraint manual validations
        qs = Company.objects.filter(organization=org)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        # Name Uniqueness Scoped by Scopes
        if branch:
            if qs.filter(branch=branch, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"A company with this name already exists in branch '{branch.name}'."})
        else:
            if qs.filter(branch__isnull=True, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": "A company with this name already exists at the organization level."})

        # Code Uniqueness Scoped by Scopes
        if code:
            if branch:
                if qs.filter(branch=branch, code__iexact=attrs['code']).exists():
                    raise serializers.ValidationError({"code": f"A company with code '{attrs['code']}' already exists in this branch."})
            else:
                if qs.filter(branch__isnull=True, code__iexact=attrs['code']).exists():
                    raise serializers.ValidationError({"code": f"A company with code '{attrs['code']}' already exists globally."})

        # Optimistic locking check
        if self.instance:
            client_version = attrs.get('version')
            if client_version is not None:
                try:
                    with transaction.atomic():
                        locked = Company.objects.select_for_update().get(id=self.instance.id)
                        if locked.version != client_version:
                            raise ConflictException()
                except Company.DoesNotExist:
                    pass
        attrs.pop('version', None)

        return attrs
