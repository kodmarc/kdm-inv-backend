from rest_framework import serializers
from organizations.models import Branch
from .models import Company

class CompanySerializer(serializers.ModelSerializer):
    # M2M field — accepts and returns a list of branch slugs.
    branches = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        many=True,
        required=False
    )
    code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Company
        fields = ['id', 'name', 'code', 'branches', 'version', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            self.fields['branches'].child_relation.queryset = Branch.objects.filter(
                organization=request.user.organization
            )

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        user = request.user
        org = user.organization

        name = attrs.get('name', self.instance.name if self.instance else None)
        code = attrs.get('code', self.instance.code if self.instance else '')

        if name:
            attrs['name'] = name.strip()
        if code:
            attrs['code'] = code.strip()

        # Uniqueness check scoped to the organization
        qs = Company.objects.filter(organization=org)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if name and qs.filter(name__iexact=attrs['name']).exists():
            raise serializers.ValidationError({"name": "A company with this name already exists."})

        if code and qs.filter(code__iexact=attrs['code']).exists():
            raise serializers.ValidationError({"code": f"A company with code '{attrs['code']}' already exists."})

        return attrs

    def create(self, validated_data):
        branches = validated_data.pop('branches', [])
        company = Company.objects.create(**validated_data)
        company.branches.set(branches)
        return company

    def update(self, instance, validated_data):
        branches = validated_data.pop('branches', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if branches is not None:
            instance.branches.set(branches)
        return instance
