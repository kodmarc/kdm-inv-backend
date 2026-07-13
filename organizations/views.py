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
        serializer.save()


class BranchDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = BranchSerializer
    permission_classes = [IsOrganizationHQUser]

    def get_queryset(self):
        return Branch.objects.filter(organization=self.request.user.organization)


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
