from django.db import transaction
from rest_framework import serializers
from django.utils import timezone
from organizations.models import Branch
from organizations.exceptions import ConflictException
from companies.models import Company
from .models import ItemCategory, Item

class ItemCategorySerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )
    code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ItemCategory
        fields = ['id', 'name', 'code', 'description', 'branch', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        validators = []  # Bypass default unique constraints validation

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        policy = org.item_creation_policy

        name = attrs.get('name', self.instance.name if self.instance else None)
        code = attrs.get('code', self.instance.code if self.instance else None)
        branch = attrs.get('branch', self.instance.branch if self.instance else None)

        # Enforce Policy Rules for Writes (Create/Update)
        if policy == 'ORG_ADMIN':
            # Centralized Mode
            if user.role not in ['ORG_ADMIN', 'ORG_USER']:
                raise serializers.ValidationError("Only HQ administrators can create or modify categories under Centralized policy.")
            if not self.instance:
                attrs['branch'] = None
                branch = None
        else:
            # Decentralized Mode
            if user.role not in ['BRANCH_ADMIN', 'USER']:
                raise serializers.ValidationError("HQ administrators cannot create or modify branch-level categories under Decentralized policy.")
            if not user.branch:
                raise serializers.ValidationError("You must be linked to a branch to create or modify categories under Decentralized policy.")
            if not self.instance:
                attrs['branch'] = user.branch
                branch = user.branch
            else:
                if 'branch' in attrs and attrs['branch'] != self.instance.branch:
                    raise serializers.ValidationError({"branch": "Category branch mapping cannot be changed after creation."})

        if name:
            attrs['name'] = name.strip()
        if code:
            attrs['code'] = code.strip()

        # Validate unique constraints manual check
        qs = ItemCategory.objects.filter(organization=org)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if branch:
            if qs.filter(branch=branch, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"A category with name '{attrs['name']}' already exists in branch '{branch.name}'."})
        else:
            if qs.filter(branch__isnull=True, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"A category with name '{attrs['name']}' already exists globally."})

        if code:
            if branch:
                if qs.filter(branch=branch, code__iexact=attrs['code']).exists():
                    raise serializers.ValidationError({"code": f"A category with code '{attrs['code']}' already exists in this branch."})
            else:
                if qs.filter(branch__isnull=True, code__iexact=attrs['code']).exists():
                    raise serializers.ValidationError({"code": f"A category with code '{attrs['code']}' already exists globally."})

        return attrs


class ItemSerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )
    category_name = serializers.ReadOnlyField(source='category.name')
    category_code = serializers.ReadOnlyField(source='category.code')
    company_name = serializers.ReadOnlyField(source='company.name')
    code = serializers.CharField(required=False, allow_blank=True)
    version = serializers.IntegerField(required=False)

    class Meta:
        model = Item
        fields = [
            'id', 'name', 'code', 'sku', 'category', 'category_name', 'category_code',
            'company', 'company_name', 'pack', 'grammage', 'purchase_rate', 'sales_rate',
            'purchase_tax', 'sales_tax', 'federal_tax', 'discount_slab_qty', 'discount_slab_rate',
            'min_stock', 'max_stock', 'is_active', 'branch', 'current_stock', 'damaged_stock', 'version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_stock', 'damaged_stock', 'created_at', 'updated_at']
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            org = request.user.organization
            self.fields['branch'].queryset = Branch.objects.filter(organization=org)
            self.fields['category'].queryset = ItemCategory.objects.filter(organization=org)
            self.fields['company'].queryset = Company.objects.filter(organization=org)

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        user = request.user
        org = user.organization
        policy = org.item_creation_policy

        name = attrs.get('name', self.instance.name if self.instance else None)
        code = attrs.get('code', self.instance.code if self.instance else None)
        branch = attrs.get('branch', self.instance.branch if self.instance else None)
        category = attrs.get('category', self.instance.category if self.instance else None)

        # Validate category organization scope
        if category and category.organization != org:
            raise serializers.ValidationError({"category": "Selected category must belong to your organization."})

        # Validate company organization scope
        company = attrs.get('company', self.instance.company if self.instance else None)
        if company and company.organization != org:
            raise serializers.ValidationError({"company": "Selected company must belong to your organization."})

        # Enforce Policy Rules for Writes (Create/Update)
        if policy == 'ORG_ADMIN':
            # Centralized Mode
            if user.role not in ['ORG_ADMIN', 'ORG_USER']:
                raise serializers.ValidationError("Only HQ administrators can directly create or modify items under Centralized policy.")
            if not self.instance:
                attrs['branch'] = None
                branch = None
        else:
            # Decentralized Mode
            if user.role not in ['BRANCH_ADMIN', 'USER']:
                raise serializers.ValidationError("HQ administrators cannot create or modify branch-level items under Decentralized policy.")
            if not user.branch:
                raise serializers.ValidationError("You must be linked to a branch to create or modify items under Decentralized policy.")
            if not self.instance:
                attrs['branch'] = user.branch
                branch = user.branch
            else:
                if 'branch' in attrs and attrs['branch'] != self.instance.branch:
                    raise serializers.ValidationError({"branch": "Item branch mapping cannot be changed after creation."})

        if name:
            attrs['name'] = name.strip()
        if code:
            attrs['code'] = code.strip()

        # Validate unique constraints manual check
        qs = Item.objects.filter(organization=org)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if branch:
            if qs.filter(branch=branch, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"An item with name '{attrs['name']}' already exists in branch '{branch.name}'."})
        else:
            if qs.filter(branch__isnull=True, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"An item with name '{attrs['name']}' already exists globally."})

        if code:
            if branch:
                if qs.filter(branch=branch, code__iexact=attrs['code']).exists():
                    raise serializers.ValidationError({"code": f"An item with code '{attrs['code']}' already exists in this branch."})
            else:
                if qs.filter(branch__isnull=True, code__iexact=attrs['code']).exists():
                    raise serializers.ValidationError({"code": f"An item with code '{attrs['code']}' already exists globally."})

        # Optimistic locking check
        if self.instance:
            client_version = attrs.get('version')
            if client_version is not None:
                try:
                    with transaction.atomic():
                        locked = Item.objects.select_for_update().get(id=self.instance.id)
                        if locked.version != client_version:
                            raise ConflictException()
                except Item.DoesNotExist:
                    pass
        attrs.pop('version', None)

        return attrs
