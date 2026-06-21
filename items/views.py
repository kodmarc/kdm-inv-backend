from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import ItemCategory, Item
from .serializers import ItemCategorySerializer, ItemSerializer
from organizations.permissions import PolicyBasedCRUDPermission

class ItemCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ItemCategorySerializer
    permission_classes = [permissions.IsAuthenticated, PolicyBasedCRUDPermission]
    policy_type = 'item'

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return ItemCategory.objects.none()

        org = user.organization
        policy = org.item_creation_policy
        qs = ItemCategory.objects.filter(organization=org)

        if policy == 'BRANCH_ADMIN':
            # Decentralized mode
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                return qs.filter(branch=user.branch).order_by('name')
            # HQ users can view all branch categories
            return qs.order_by('name')
        else:
            # Centralized mode: global categories (where branch is null)
            return qs.filter(branch__isnull=True).order_by('name')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated, PolicyBasedCRUDPermission]
    policy_type = 'item'

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return Item.objects.none()

        org = user.organization
        policy = org.item_creation_policy
        qs = Item.objects.filter(organization=org)

        # Optional query filtering by company code
        company_code = self.request.query_params.get('company_code')
        if company_code:
            qs = qs.filter(company__code__iexact=company_code)

        if policy == 'BRANCH_ADMIN':
            # Decentralized mode
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                return qs.filter(branch=user.branch).order_by('name')
            # HQ users can view all branch items
            return qs.order_by('name')
        else:
            # Centralized mode: global items (where branch is null)
            return qs.filter(branch__isnull=True).order_by('name')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
