from rest_framework import serializers
from django.utils.text import slugify
from .models import Branch

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Branch name cannot be empty.")
        
        # Access the user and organization from context
        request = self.context.get('request')
        if request and request.user:
            org = request.user.organization
            slug = slugify(name)
            # Check if this slug already exists in this organization
            if Branch.objects.filter(organization=org, slug=slug).exists():
                raise serializers.ValidationError("A branch with this name or slug already exists in your organization.")
        
        return name

    def create(self, validated_data):
        request = self.context.get('request')
        org = request.user.organization
        name = validated_data['name']
        slug = slugify(name)
        
        return Branch.objects.create(
            organization=org,
            name=name,
            slug=slug
        )
