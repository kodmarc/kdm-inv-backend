from rest_framework import serializers
from companies.models import Company
from .models import ItemCategory, Item

class ItemCategorySerializer(serializers.ModelSerializer):
    code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ItemCategory
        fields = ['id', 'name', 'code', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        validators = []

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        org = request.user.organization
        name = attrs.get('name', self.instance.name if self.instance else None)
        code = attrs.get('code', self.instance.code if self.instance else '')

        if name:
            attrs['name'] = name.strip()
        if code:
            attrs['code'] = code.strip()

        qs = ItemCategory.objects.filter(organization=org)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if name and qs.filter(name__iexact=attrs['name']).exists():
            raise serializers.ValidationError({"name": f"A category with name '{attrs['name']}' already exists."})

        if code and qs.filter(code__iexact=attrs['code']).exists():
            raise serializers.ValidationError({"code": f"A category with code '{attrs['code']}' already exists."})

        return attrs


class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    category_code = serializers.ReadOnlyField(source='category.code')
    company_name = serializers.ReadOnlyField(source='company.name')
    code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Item
        fields = [
            'id', 'name', 'code', 'sku', 'category', 'category_name', 'category_code',
            'company', 'company_name', 'pack', 'grammage', 'purchase_rate', 'sales_rate',
            'purchase_tax', 'sales_tax', 'federal_tax', 'discount_slab_qty', 'discount_slab_rate',
            'min_stock', 'max_stock', 'is_active', 'current_stock', 'damaged_stock',
            'version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_stock', 'damaged_stock', 'version', 'created_at', 'updated_at']
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            org = request.user.organization
            self.fields['category'].queryset = ItemCategory.objects.filter(organization=org)
            self.fields['company'].queryset = Company.objects.filter(organization=org)

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        org = request.user.organization
        name = attrs.get('name', self.instance.name if self.instance else None)
        code = attrs.get('code', self.instance.code if self.instance else '')

        # Validate category and company belong to this org
        category = attrs.get('category', self.instance.category if self.instance else None)
        if category and category.organization != org:
            raise serializers.ValidationError({"category": "Selected category must belong to your organization."})

        company = attrs.get('company', self.instance.company if self.instance else None)
        if company and company.organization != org:
            raise serializers.ValidationError({"company": "Selected company must belong to your organization."})

        if name:
            attrs['name'] = name.strip()
        if code:
            attrs['code'] = code.strip()

        qs = Item.objects.filter(organization=org)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if name and qs.filter(name__iexact=attrs['name']).exists():
            raise serializers.ValidationError({"name": f"An item with name '{attrs['name']}' already exists."})

        if code and qs.filter(code__iexact=attrs['code']).exists():
            raise serializers.ValidationError({"code": f"An item with code '{attrs['code']}' already exists."})

        return attrs
