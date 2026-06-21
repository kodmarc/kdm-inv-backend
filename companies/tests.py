from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from organizations.models import Organization, Branch
from .models import Company

User = get_user_model()

class CompanyRegisterTests(APITestCase):
    def setUp(self):
        # 1. Organization A: Centralized Policy (HQ Admin creates, all can read)
        self.org_a = Organization.objects.create(
            org_id='orga1',
            name='Organization A',
            company_creation_policy=Organization.Policy.ORG_ADMIN
        )
        self.branch_a = Branch.objects.create(
            organization=self.org_a,
            name='Branch A',
            slug='branch-a'
        )
        
        self.admin_a = User.objects.create_user(
            username='admin_a',
            password='password123',
            organization=self.org_a,
            role=User.Role.ORG_ADMIN
        )
        self.branch_admin_a = User.objects.create_user(
            username='b_admin_a',
            password='password123',
            organization=self.org_a,
            branch=self.branch_a,
            role=User.Role.BRANCH_ADMIN
        )

        # 2. Organization B: Decentralized Policy (Branch scoped visibility & creation)
        self.org_b = Organization.objects.create(
            org_id='orgb1',
            name='Organization B',
            company_creation_policy=Organization.Policy.BRANCH_ADMIN
        )
        self.branch_b1 = Branch.objects.create(
            organization=self.org_b,
            name='Branch B1',
            slug='branch-b1'
        )
        self.branch_b2 = Branch.objects.create(
            organization=self.org_b,
            name='Branch B2',
            slug='branch-b2'
        )

        self.admin_b = User.objects.create_user(
            username='admin_b',
            password='password123',
            organization=self.org_b,
            role=User.Role.ORG_ADMIN
        )
        self.branch_admin_b1 = User.objects.create_user(
            username='b_admin_b1',
            password='password123',
            organization=self.org_b,
            branch=self.branch_b1,
            role=User.Role.BRANCH_ADMIN
        )
        self.branch_admin_b2 = User.objects.create_user(
            username='b_admin_b2',
            password='password123',
            organization=self.org_b,
            branch=self.branch_b2,
            role=User.Role.BRANCH_ADMIN
        )

        # Endpoint helper
        self.list_create_url = reverse('company-list')

    # --- Centralized Scoping Tests (Org A) ---

    def test_centralized_hq_admin_can_create_company(self):
        self.client.force_authenticate(user=self.admin_a)
        payload = {'name': 'Central Co'}
        response = self.client.post(self.list_create_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['branch'])
        self.assertEqual(response.data['code'], 'COMP-0001')

    def test_centralized_branch_admin_blocked_from_creating(self):
        self.client.force_authenticate(user=self.branch_admin_a)
        payload = {'name': 'Branch Stolen Co'}
        response = self.client.post(self.list_create_url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_centralized_all_users_can_view_global_companies(self):
        # Create a company under admin A
        Company.objects.create(organization=self.org_a, name='Global Co', code='COMP-0001')

        # Org Admin checks
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Branch Admin checks (should see global company)
        self.client.force_authenticate(user=self.branch_admin_a)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Global Co')

    # --- Decentralized Scoping Tests (Org B) ---

    def test_decentralized_branch_admin_creates_local_company(self):
        self.client.force_authenticate(user=self.branch_admin_b1)
        payload = {'name': 'Local B1 Co'}
        response = self.client.post(self.list_create_url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['branch'], self.branch_b1.slug)
        self.assertEqual(response.data['code'], 'COMP-0001')

    def test_decentralized_branch_isolation(self):
        # B1 creates Company
        Company.objects.create(organization=self.org_b, branch=self.branch_b1, name='B1 Company', code='COMP-0001')
        # B2 creates Company
        Company.objects.create(organization=self.org_b, branch=self.branch_b2, name='B2 Company', code='COMP-0001')

        # B1 admin lists (should only see B1 Company)
        self.client.force_authenticate(user=self.branch_admin_b1)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'B1 Company')

        # B2 admin lists (should only see B2 Company)
        self.client.force_authenticate(user=self.branch_admin_b2)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'B2 Company')

        # Org Admin lists (should see both)
        self.client.force_authenticate(user=self.admin_b)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    # --- Uniqueness Constraints Verification ---

    def test_unique_constraint_validations(self):
        self.client.force_authenticate(user=self.admin_a)
        
        # Create global company
        self.client.post(self.list_create_url, {'name': 'Duplicate Co', 'code': 'DUP-001'})
        
        # Try to duplicate name globally
        response = self.client.post(self.list_create_url, {'name': 'Duplicate Co', 'code': 'NEW-002'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

        # Try to duplicate code globally
        response = self.client.post(self.list_create_url, {'name': 'Unique Co', 'code': 'DUP-001'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('code', response.data)

    def test_optimistic_locking(self):
        self.client.force_authenticate(user=self.admin_a)
        
        # Create a company (version starts at 1)
        company = Company.objects.create(organization=self.org_a, name='Locking Co', code='LOCK-001')
        self.assertEqual(company.version, 1)
        
        detail_url = reverse('company-detail', kwargs={'pk': company.id})
        
        # 1. Update with mismatching version -> expect 409 Conflict
        response = self.client.put(detail_url, {
            'name': 'Updated Mismatching',
            'code': 'LOCK-001',
            'version': 99
        })
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        
        # Verify db wasn't modified
        company.refresh_from_db()
        self.assertEqual(company.name, 'Locking Co')
        self.assertEqual(company.version, 1)

        # 2. Update with matching version -> expect 200 OK
        response = self.client.put(detail_url, {
            'name': 'Updated Matching',
            'code': 'LOCK-001',
            'version': 1
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify db was updated and version incremented
        company.refresh_from_db()
        self.assertEqual(company.name, 'Updated Matching')
        self.assertEqual(company.version, 2)

        # 3. Update without version parameter -> expect success (backward compatibility)
        response = self.client.put(detail_url, {
            'name': 'Updated No Version',
            'code': 'LOCK-001'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company.refresh_from_db()
        self.assertEqual(company.name, 'Updated No Version')
        self.assertEqual(company.version, 3)

