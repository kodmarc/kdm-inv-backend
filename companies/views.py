from rest_framework import viewsets, permissions
from .models import Company
from .serializers import CompanySerializer
from organizations.permissions import IsOrganizationHQUser

class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer

    def get_permissions(self):
        # All authenticated users can read; only HQ users can write.
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOrganizationHQUser()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return Company.objects.none()

        qs = Company.objects.filter(organization=user.organization)

        # Branch users only see companies assigned to their branch via the M2M.
        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            if user.branch:
                return qs.filter(branches=user.branch).order_by('name')
            return Company.objects.none()

        # HQ users see all companies in the organization.
        return qs.prefetch_related('branches').order_by('name')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
