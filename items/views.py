from rest_framework import viewsets, permissions
from .models import ItemCategory, Item
from .serializers import ItemCategorySerializer, ItemSerializer
from organizations.permissions import IsOrganizationHQUser

class ItemCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ItemCategorySerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOrganizationHQUser()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return ItemCategory.objects.none()
        # Categories are org-level — all authenticated users can read them all.
        return ItemCategory.objects.filter(organization=user.organization).order_by('name')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOrganizationHQUser()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return Item.objects.none()

        qs = Item.objects.filter(organization=user.organization)

        # Optional filter by company code (used by branch pages to load company-specific items).
        company_code = self.request.query_params.get('company_code')
        if company_code:
            qs = qs.filter(company__code__iexact=company_code)

        # Branch users see items for companies assigned to their branch.
        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            if user.branch:
                qs = qs.filter(company__branches=user.branch)
            else:
                return Item.objects.none()

        return qs.order_by('name')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
