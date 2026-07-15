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

        # Category filter (for HQ portal)
        category_id = self.request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)

        # Sorting parameters
        sort_by = self.request.query_params.get('sort_by', 'name')
        sort_order = self.request.query_params.get('sort_order', 'asc')
        
        # Map frontend sort options to model fields
        sort_field_map = {
            'name': 'name',
            'sales_rate': 'sales_rate',
            'purchase_rate': 'purchase_rate',
            'created_at': 'created_at',
        }
        
        field = sort_field_map.get(sort_by, 'name')
        
        # Apply order
        if sort_order == 'desc':
            field = f'-{field}'
        
        return qs.order_by(field)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)