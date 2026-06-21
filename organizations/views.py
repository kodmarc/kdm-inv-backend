from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Branch, Organization
from .serializers import BranchSerializer
from .permissions import IsOrganizationHQUser

class BranchListCreateView(generics.ListCreateAPIView):
    serializer_class = BranchSerializer
    permission_classes = [IsOrganizationHQUser]

    def get_queryset(self):
        # Enforce multi-tenant data isolation at query layer
        return Branch.objects.filter(organization=self.request.user.organization).order_by('-created_at')

    def perform_create(self, serializer):
        # Serializer's create method handles linking the user's organization automatically
        serializer.save()


class PublicBranchListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        org_id = request.query_params.get('org_id')
        if not org_id:
            return Response(
                {"error": "Organization ID parameter is required.", "code": "REQUIRED_PARAMETER_MISSING"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        branches = Branch.objects.filter(organization__org_id=org_id.lower().strip()).order_by('name')
        data = [{"name": b.name, "slug": b.slug} for b in branches]
        return Response(data, status=status.HTTP_200_OK)


class OrganizationSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role not in [user.Role.ORG_ADMIN, user.Role.ORG_USER]:
            return Response({"error": "Only HQ users can access organization settings."}, status=status.HTTP_403_FORBIDDEN)
        
        org = user.organization
        return Response({
            "name": org.name,
            "org_id": org.org_id,
            "company_creation_policy": org.company_creation_policy,
            "item_creation_policy": org.item_creation_policy,
        })

    def put(self, request):
        user = request.user
        if user.role != user.Role.ORG_ADMIN:
            return Response({"error": "Only Organization Admins can modify settings."}, status=status.HTTP_403_FORBIDDEN)
        
        org = user.organization
        company_policy = request.data.get('company_creation_policy')
        item_policy = request.data.get('item_creation_policy')
        org_name = request.data.get('name')

        if company_policy and company_policy not in Organization.Policy.values:
            return Response({"error": "Invalid company creation policy."}, status=status.HTTP_400_BAD_REQUEST)
        if item_policy and item_policy not in Organization.Policy.values:
            return Response({"error": "Invalid item creation policy."}, status=status.HTTP_400_BAD_REQUEST)

        if org_name:
            org.name = org_name.strip()
        if company_policy:
            org.company_creation_policy = company_policy
        if item_policy:
            org.item_creation_policy = item_policy
        
        org.save()
        return Response({
            "name": org.name,
            "org_id": org.org_id,
            "company_creation_policy": org.company_creation_policy,
            "item_creation_policy": org.item_creation_policy,
        }, status=status.HTTP_200_OK)
