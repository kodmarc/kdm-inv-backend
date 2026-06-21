from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from organizations.models import Organization, Branch
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class BranchAPITests(APITestCase):

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=False)  # Keep CSRF disabled for basic testing here unless testing CSRF
        self.branch_url = reverse('branch_list_create')
        
        # Org A setup
        self.org_a = Organization.objects.create(org_id="orga1", name="Organization A")
        self.admin_a = User.objects.create_user(
            username="admin_a", password="securepassword123", organization=self.org_a, role=User.Role.ORG_ADMIN
        )
        self.kpo_a = User.objects.create_user(
            username="kpo_a", password="securepassword123", organization=self.org_a, role=User.Role.KPO
        )
        
        # Org B setup
        self.org_b = Organization.objects.create(org_id="orgb1", name="Organization B")
        self.admin_b = User.objects.create_user(
            username="admin_b", password="securepassword123", organization=self.org_b, role=User.Role.ORG_ADMIN
        )

    def authenticate_user(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.cookies['access_token'] = str(refresh.access_token)
        self.client.cookies['refresh_token'] = str(refresh)

    def test_create_branch_success(self):
        """TC-ORG-01: Verify ORG_ADMIN can create a branch successfully."""
        self.authenticate_user(self.admin_a)
        
        payload = {"name": "Clifton Mart"}
        response = self.client.post(self.branch_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Clifton Mart")
        self.assertEqual(response.data['slug'], "clifton-mart")
        
        # Verify in DB
        branch = Branch.objects.get(organization=self.org_a, slug="clifton-mart")
        self.assertEqual(branch.name, "Clifton Mart")

    def test_list_branches_isolation(self):
        """TC-ORG-03: Verify listing branches only returns records belonging to the active organization."""
        # Create branches in Org A
        Branch.objects.create(organization=self.org_a, name="Branch A1", slug="branch-a1")
        Branch.objects.create(organization=self.org_a, name="Branch A2", slug="branch-a2")
        
        # Create branches in Org B
        Branch.objects.create(organization=self.org_b, name="Branch B1", slug="branch-b1")
        
        # Log in as Org A Admin
        self.authenticate_user(self.admin_a)
        response = self.client.get(self.branch_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return Org A branches (2 items)
        self.assertEqual(len(response.data), 2)
        slugs = [item['slug'] for item in response.data]
        self.assertIn("branch-a1", slugs)
        self.assertNotIn("branch-b1", slugs)

    def test_duplicate_slug_blocked_in_same_org(self):
        """TC-ORG-04: Verify branch slug uniqueness constraint is enforced within the same organization."""
        self.authenticate_user(self.admin_a)
        
        # Create Clifton Mart first
        payload = {"name": "Clifton Mart"}
        self.client.post(self.branch_url, payload, format='json')
        
        # Try to create it again -> expect validation fail
        response = self.client.post(self.branch_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_duplicate_slug_allowed_across_different_orgs(self):
        """TC-ORG-05: Verify identical branch names are allowed in different organizations."""
        # Create Clifton Mart in Org A
        self.authenticate_user(self.admin_a)
        response_a = self.client.post(self.branch_url, {"name": "Clifton Mart"}, format='json')
        self.assertEqual(response_a.status_code, status.HTTP_201_CREATED)
        
        # Create Clifton Mart in Org B -> expect success
        self.authenticate_user(self.admin_b)
        response_b = self.client.post(self.branch_url, {"name": "Clifton Mart"}, format='json')
        self.assertEqual(response_b.status_code, status.HTTP_201_CREATED)

    def test_non_org_user_role_blocked(self):
        """TC-ORG-02: Verify non-HQ roles (like KPO) cannot create or view branches."""
        self.authenticate_user(self.kpo_a)
        
        # Try to view branches -> expect 403
        response_get = self.client.get(self.branch_url)
        self.assertEqual(response_get.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to create a branch -> expect 403
        response_post = self.client.post(self.branch_url, {"name": "New Branch"}, format='json')
        self.assertEqual(response_post.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_branch_list(self):
        """TC-FE-05: Verify public branch listing works without authentication."""
        # Create a branch
        Branch.objects.create(organization=self.org_a, name="Karachi Branch", slug="karachi-branch")
        
        # Access unauthenticated
        self.client.cookies.clear()
        public_url = reverse('public_branch_list')
        
        response = self.client.get(f"{public_url}?org_id=orga1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['slug'], 'karachi-branch')
        
        # Request with missing org_id -> expect 400
        response_error = self.client.get(public_url)
        self.assertEqual(response_error.status_code, status.HTTP_400_BAD_REQUEST)

    def test_organization_settings_view_and_update(self):
        """Verify fetching and updating organization policy settings."""
        settings_url = reverse('org_settings')
        org_user = User.objects.create_user(
            username="org_user_a", password="securepassword123", organization=self.org_a, role=User.Role.ORG_USER
        )

        # 1. ORG_USER can view settings
        self.authenticate_user(org_user)
        response = self.client.get(settings_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_creation_policy'], 'ORG_ADMIN')

        # 2. ORG_USER cannot update settings
        response_put = self.client.put(settings_url, {"company_creation_policy": "BRANCH_ADMIN"}, format='json')
        self.assertEqual(response_put.status_code, status.HTTP_403_FORBIDDEN)

        # 3. ORG_ADMIN can update settings
        self.authenticate_user(self.admin_a)
        response_update = self.client.put(settings_url, {
            "name": "Updated Organization Name",
            "company_creation_policy": "BRANCH_ADMIN",
            "item_creation_policy": "BRANCH_ADMIN"
        }, format='json')
        self.assertEqual(response_update.status_code, status.HTTP_200_OK)
        self.assertEqual(response_update.data['name'], "Updated Organization Name")
        self.assertEqual(response_update.data['company_creation_policy'], "BRANCH_ADMIN")

        # Verify DB is updated
        self.org_a.refresh_from_db()
        self.assertEqual(self.org_a.name, "Updated Organization Name")
        self.assertEqual(self.org_a.company_creation_policy, "BRANCH_ADMIN")

        # 4. Non-HQ users (like KPO) cannot access settings
        self.authenticate_user(self.kpo_a)
        response_denied = self.client.get(settings_url)
        self.assertEqual(response_denied.status_code, status.HTTP_403_FORBIDDEN)
