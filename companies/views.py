from rest_framework import viewsets, permissions
from .models import Company
from .serializers import CompanySerializer
from organizations.permissions import PolicyBasedCRUDPermission

class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated, PolicyBasedCRUDPermission]
    policy_type = 'company'

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return Company.objects.none()

        org = user.organization
        policy = org.company_creation_policy

        # Base filter: always isolate by Organization
        qs = Company.objects.filter(organization=org)

        if policy == 'BRANCH_ADMIN':
            # Decentralized mode
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                # Branch users only see companies assigned to their own branch
                return qs.filter(branch=user.branch).order_by('name')
            # HQ users (ORG_ADMIN, ORG_USER) can see all branch companies
            return qs.order_by('name')
        else:
            # Centralized mode: all users see organization-wide (global) companies
            return qs.filter(branch__isnull=True).order_by('name')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

