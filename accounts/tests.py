from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from organizations.models import Organization, Branch
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class CustomAuthTests(APITestCase):

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)  # Enforce CSRF checks in tests
        self.signup_url = reverse('signup')
        self.login_org_url = reverse('login_org')
        self.login_branch_url = reverse('login_branch')
        self.logout_url = reverse('logout')
        self.refresh_url = reverse('token_refresh')
        self.me_url = reverse('me')

    def test_signup_success(self):
        """TC-API-01: Verify Organization Signup creates Organization and ORG_ADMIN user."""
        payload = {
            "org_id": "kdmtest1",
            "org_name": "Test Organization",
            "username": "test_admin",
            "password": "securepassword123"
        }
        response = self.client.post(self.signup_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertIn('csrf_token', response.data)
        
        # Verify DB records
        org_exists = Organization.objects.filter(org_id="kdmtest1").exists()
        user_exists = User.objects.filter(username="test_admin", role=User.Role.ORG_ADMIN).exists()
        self.assertTrue(org_exists)
        self.assertTrue(user_exists)

    def test_signup_duplicate_org_id_fails(self):
        """TC-API-02: Verify duplicate signup blocks with 400 validation error."""
        # Pre-create org
        Organization.objects.create(org_id="kdmduplicate1", name="First")
        
        payload = {
            "org_id": "kdmduplicate1",
            "org_name": "Second",
            "username": "second_admin",
            "password": "securepassword123"
        }
        response = self.client.post(self.signup_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("org_id", response.data['error'])

    def test_signup_short_org_id_fails(self):
        """Verify org_id of less than 5 characters is rejected by the backend API."""
        payload = {
            "org_id": "kdm1",
            "org_name": "Short Org ID Test",
            "username": "short_admin",
            "password": "securepassword123"
        }
        response = self.client.post(self.signup_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("org_id", response.data['error'])

    def test_signup_special_chars_org_id_fails(self):
        """Verify org_id with special characters is rejected by the backend API."""
        payload = {
            "org_id": "kdm-101",
            "org_name": "Special Chars Org ID Test",
            "username": "special_admin",
            "password": "securepassword123"
        }
        response = self.client.post(self.signup_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("org_id", response.data['error'])

    def test_signup_no_numbers_org_id_fails(self):
        """Verify org_id without numbers is rejected by the backend API."""
        payload = {
            "org_id": "kdmorg",
            "org_name": "No Numbers Org ID Test",
            "username": "nonum_admin",
            "password": "securepassword123"
        }
        response = self.client.post(self.signup_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("org_id", response.data['error'])

    def test_signup_no_letters_org_id_fails(self):
        """Verify org_id without letters is rejected by the backend API."""
        payload = {
            "org_id": "12345",
            "org_name": "No Letters Org ID Test",
            "username": "nolet_admin",
            "password": "securepassword123"
        }
        response = self.client.post(self.signup_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("org_id", response.data['error'])

    def test_signup_short_password_fails(self):
        """Verify passwords shorter than 8 characters are rejected by the backend API."""
        payload = {
            "org_id": "kdm101",
            "org_name": "Short Password Test",
            "username": "short_pass_admin",
            "password": "pass123"
        }
        response = self.client.post(self.signup_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data['error'])


    def test_login_org_success(self):
        org = Organization.objects.create(org_id="kdmorg1", name="Org")
        User.objects.create_superuser(
            username="org_owner", password="securepassword123", organization=org, role=User.Role.ORG_ADMIN
        )

        payload = {
            "org_id": "kdmorg1",
            "username": "org_owner",
            "password": "securepassword123",
            "role": "ORG_ADMIN"
        }
        response = self.client.post(self.login_org_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.cookies)

    def test_login_branch_isolation(self):
        """TC-API-03: Verify Branch Member login is isolated by branch_slug and role."""
        org = Organization.objects.create(org_id="kdmbranch1", name="Org")
        branch_a = Branch.objects.create(organization=org, name="Branch A", slug="branch-a")
        branch_b = Branch.objects.create(organization=org, name="Branch B", slug="branch-b")
        
        # Cashier registered strictly under Branch A
        cashier = User.objects.create_user(
            username="cashier1",
            password="securepassword123",
            organization=org,
            branch=branch_a,
            role=User.Role.KPO
        )

        # Attempt to login under Branch B context
        payload = {
            "org_id": "kdmbranch1",
            "branch_slug": "branch-b",  # Wrong branch
            "username": "cashier1",
            "password": "securepassword123",
            "role": "KPO"
        }
        response = self.client.post(self.login_branch_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Login under correct Branch A context
        payload["branch_slug"] = "branch-a"
        response = self.client.post(self.login_branch_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.cookies)

    def test_csrf_protection_enforced(self):
        """TC-API-04: Verify authenticated write requests without CSRF token headers fail with 403."""
        org = Organization.objects.create(org_id="kdmcsrf1", name="Org")
        user = User.objects.create_user(
            username="test_user", password="securepassword123", organization=org, role=User.Role.ORG_ADMIN
        )

        # 1. Login to get valid JWT cookies (but do not set the client-level CSRF header yet)
        payload = {
            "org_id": "kdmcsrf1",
            "username": "test_user",
            "password": "securepassword123",
            "role": "ORG_ADMIN"
        }
        login_response = self.client.post(self.login_org_url, payload, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        csrf_token = login_response.data['csrf_token']

        # Clear credentials header to test raw cookie session
        self.client.credentials() 

        # 2. Attempt to create branch (POST request) without CSRF header -> expect 403
        branches_url = reverse('branch_list_create')
        branch_payload = {"name": "Test Branch", "slug": "test-branch"}
        response = self.client.post(branches_url, branch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Repeat request with correct X-CSRFToken header -> expect 201 CREATED
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
        response_success = self.client.post(branches_url, branch_payload, format='json')
        self.assertEqual(response_success.status_code, status.HTTP_201_CREATED)

    def test_token_refresh_rotation(self):
        """TC-API-05: Verify refreshing rotates tokens and invalidates the previous refresh token."""
        org = Organization.objects.create(org_id="kdmrefresh1", name="Org")
        user = User.objects.create_user(
            username="test_user", password="securepassword123", organization=org, role=User.Role.ORG_ADMIN
        )

        # Login to get cookies and initial CSRF token
        payload = {
            "org_id": "kdmrefresh1",
            "username": "test_user",
            "password": "securepassword123",
            "role": "ORG_ADMIN"
        }
        login_response = self.client.post(self.login_org_url, payload, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        csrf_token = login_response.data['csrf_token']

        # Get the refresh token cookie
        refresh_cookie = login_response.cookies.get('refresh_token').value

        # Perform first refresh (passing the CSRF token)
        self.client.cookies['refresh_token'] = refresh_cookie
        response = self.client.post(self.refresh_url, {}, format='json', HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify old refresh token is blacklisted by trying to reuse it (passing the CSRF token)
        self.client.cookies['refresh_token'] = refresh_cookie
        response_reuse = self.client.post(self.refresh_url, {}, format='json', HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response_reuse.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_management_list_scoping(self):
        """Verify role-based scoping and visibility restrictions for listing users."""
        org_a = Organization.objects.create(org_id="orgacorp", name="Org A")
        org_b = Organization.objects.create(org_id="orgbcorp", name="Org B")
        
        branch_a1 = Branch.objects.create(organization=org_a, name="Branch A1", slug="branch-a1")
        branch_a2 = Branch.objects.create(organization=org_a, name="Branch A2", slug="branch-a2")
        
        # Org A Admin
        admin_a = User.objects.create_superuser(
            username="admin_a", password="securepassword123", organization=org_a, role=User.Role.ORG_ADMIN
        )
        # Org A User
        user_a = User.objects.create_user(
            username="user_a", password="securepassword123", organization=org_a, role=User.Role.ORG_USER
        )
        # Branch A1 Admin
        branch_admin_a1 = User.objects.create_user(
            username="branch_admin_a1", password="securepassword123", organization=org_a, branch=branch_a1, role=User.Role.BRANCH_ADMIN
        )
        # Branch A1 Cashier
        kpo_a1 = User.objects.create_user(
            username="kpo_a1", password="securepassword123", organization=org_a, branch=branch_a1, role=User.Role.KPO
        )
        # Branch A2 Admin
        branch_admin_a2 = User.objects.create_user(
            username="branch_admin_a2", password="securepassword123", organization=org_a, branch=branch_a2, role=User.Role.BRANCH_ADMIN
        )
        
        # Org B Admin (totally isolated)
        admin_b = User.objects.create_superuser(
            username="admin_b", password="securepassword123", organization=org_b, role=User.Role.ORG_ADMIN
        )

        users_list_url = reverse('user_management-list')

        # 1. Org A Admin requests list -> should see all 5 Org A users (and 0 Org B users)
        self.client.force_authenticate(user=admin_a)
        response = self.client.get(users_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        usernames = [u['username'] for u in response.data]
        self.assertIn("admin_a", usernames)
        self.assertIn("branch_admin_a1", usernames)
        self.assertNotIn("admin_b", usernames)

        # 2. Branch A1 Admin requests list -> should see only Branch A1 users (branch_admin_a1 and kpo_a1)
        self.client.force_authenticate(user=branch_admin_a1)
        response = self.client.get(users_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        usernames = [u['username'] for u in response.data]
        self.assertIn("branch_admin_a1", usernames)
        self.assertIn("kpo_a1", usernames)
        self.assertNotIn("branch_admin_a2", usernames)

        # 3. KPO Cashier requests list -> blocked with 403 Forbidden
        self.client.force_authenticate(user=kpo_a1)
        response = self.client.get(users_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_management_creation_scoping(self):
        """Verify role-based boundary restrictions on user creation."""
        org = Organization.objects.create(org_id="orgacorp", name="Org")
        branch_1 = Branch.objects.create(organization=org, name="Branch 1", slug="branch-1")
        branch_2 = Branch.objects.create(organization=org, name="Branch 2", slug="branch-2")

        admin = User.objects.create_superuser(
            username="admin", password="securepassword123", organization=org, role=User.Role.ORG_ADMIN
        )
        branch_admin = User.objects.create_user(
            username="branch_admin", password="securepassword123", organization=org, branch=branch_1, role=User.Role.BRANCH_ADMIN
        )

        users_list_url = reverse('user_management-list')

        # 1. Branch Admin tries to create a KPO under Branch 2 -> fails validation
        self.client.force_authenticate(user=branch_admin)
        payload_wrong_branch = {
            "username": "kpo_b2",
            "email": "kpo2@org.com",
            "role": "KPO",
            "branch": "branch-2",
            "password": "securepassword123"
        }
        response = self.client.post(users_list_url, payload_wrong_branch, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("branch", response.data)

        # 2. Branch Admin tries to create an HQ Admin -> fails validation
        payload_hq_role = {
            "username": "new_hq_admin",
            "email": "hq@org.com",
            "role": "ORG_ADMIN",
            "branch": "branch-1",
            "password": "securepassword123"
        }
        response = self.client.post(users_list_url, payload_hq_role, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data)

        # 3. Branch Admin creates a KPO under Branch 1 -> succeeds
        payload_correct = {
            "username": "kpo_correct",
            "email": "kpo1@org.com",
            "role": "KPO",
            "branch": "branch-1",
            "password": "securepassword123"
        }
        response = self.client.post(users_list_url, payload_correct, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="kpo_correct", branch=branch_1).exists())

        # 4. Org Admin creates an ORG_USER -> succeeds
        self.client.force_authenticate(user=admin)
        payload_org_user = {
            "username": "org_user_new",
            "email": "orguser@org.com",
            "role": "ORG_USER",
            "password": "securepassword123"
        }
        response = self.client.post(users_list_url, payload_org_user, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="org_user_new", role=User.Role.ORG_USER).exists())

    def test_user_management_self_lockout_prevention(self):
        """Verify that admins cannot delete, disable, or de-privilege themselves."""
        org = Organization.objects.create(org_id="orgacorp", name="Org")
        admin = User.objects.create_superuser(
            username="admin", password="securepassword123", organization=org, role=User.Role.ORG_ADMIN
        )

        user_detail_url = reverse('user_management-detail', kwargs={'pk': admin.id})
        self.client.force_authenticate(user=admin)

        # 1. Try to change own role to ORG_USER -> fails validation
        response = self.client.patch(user_detail_url, {"role": "ORG_USER"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data)

        # 2. Try to disable own account -> fails validation
        response = self.client.patch(user_detail_url, {"is_active": False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_active", response.data)

        # 3. Try to delete own account -> fails validation
        response = self.client.delete(user_detail_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify admin remains active and ORG_ADMIN
        admin.refresh_from_db()
        self.assertTrue(admin.is_active)
        self.assertEqual(admin.role, User.Role.ORG_ADMIN)

