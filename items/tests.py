from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from organizations.models import Organization, Branch
from companies.models import Company
from .models import ItemCategory, Item

User = get_user_model()

class ItemModuleTests(APITestCase):
    def setUp(self):
        # Create Organization
        self.org = Organization.objects.create(
            name="Test Organization",
            org_id="testorg101",
            company_creation_policy=Organization.Policy.ORG_ADMIN,
            item_creation_policy=Organization.Policy.ORG_ADMIN
        )

        # Create Branches
        self.branch_a = Branch.objects.create(
            organization=self.org,
            name="Branch A",
            slug="branch-a"
        )
        self.branch_b = Branch.objects.create(
            organization=self.org,
            name="Branch B",
            slug="branch-b"
        )

        # Create Users
        self.org_admin = User.objects.create_user(
            username="orgadmin",
            password="password123",
            organization=self.org,
            role=User.Role.ORG_ADMIN
        )
        self.branch_admin_a = User.objects.create_user(
            username="branchadmina",
            password="password123",
            organization=self.org,
            branch=self.branch_a,
            role=User.Role.BRANCH_ADMIN
        )
        self.branch_admin_b = User.objects.create_user(
            username="branchadminb",
            password="password123",
            organization=self.org,
            branch=self.branch_b,
            role=User.Role.BRANCH_ADMIN
        )

        # Create Company (useful for item mappings)
        self.company = Company.objects.create(
            organization=self.org,
            name="Test Company",
            code="COMP-01"
        )

    def test_centralized_policy_direct_creation(self):
        """
        Under Centralized policy:
        - HQ Admin can create categories and items directly (branch=null).
        - Branch Admin is blocked from direct creation.
        """
        self.org.item_creation_policy = Organization.Policy.ORG_ADMIN
        self.org.save()

        # 1. HQ Admin creates category
        self.client.force_authenticate(user=self.org_admin)
        cat_url = reverse('item-category-list')
        cat_data = {
            "name": "Dairy",
            "description": "Milk products"
        }
        response = self.client.post(cat_url, cat_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['branch'])
        self.assertEqual(response.data['code'], "CAT-0001")
        category_id = response.data['id']

        # 2. HQ Admin creates item
        item_url = reverse('item-list')
        item_data = {
            "name": "Milk 1L",
            "category": category_id,
            "company": self.company.id,
            "pack": 12,
            "grammage": "1000 ml",
            "purchase_rate": "150.00",
            "sales_rate": "170.00",
            "sales_tax": "17.00"
        }
        response = self.client.post(item_url, item_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['branch'])
        self.assertEqual(response.data['code'], "ITEM-0001")

        # 3. Branch Admin attempts direct category creation (should be blocked)
        self.client.force_authenticate(user=self.branch_admin_a)
        response = self.client.post(cat_url, {
            "name": "Beverages"
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Branch Admin attempts direct item creation (should be blocked)
        response = self.client.post(item_url, {
            "name": "Pepsi 1.5L",
            "category": category_id
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_decentralized_policy_workflow(self):
        """
        Under Decentralized policy:
        - Branch Admin creates items and categories directly scoped to their branch.
        - Branch isolation is enforced.
        - HQ Admin cannot create items under decentralized policy.
        """
        self.org.item_creation_policy = Organization.Policy.BRANCH_ADMIN
        self.org.save()

        # 1. Branch Admin A creates category and item
        self.client.force_authenticate(user=self.branch_admin_a)
        cat_url = reverse('item-category-list')
        response = self.client.post(cat_url, {"name": "Fresh Goods"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['branch'], self.branch_a.slug)
        cat_a_id = response.data['id']

        item_url = reverse('item-list')
        response = self.client.post(item_url, {
            "name": "Brown Bread",
            "category": cat_a_id
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['branch'], self.branch_a.slug)
        item_a_id = response.data['id']

        # 2. Branch Admin B creates category and item
        self.client.force_authenticate(user=self.branch_admin_b)
        response = self.client.post(cat_url, {"name": "Fresh Goods"})  # Same name, allowed because isolated by branch!
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['branch'], self.branch_b.slug)
        cat_b_id = response.data['id']

        # 3. Branch Admin B list categories: should NOT see Branch A's category
        response = self.client.get(cat_url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], cat_b_id)

        # 4. Branch Admin B list items: should NOT see Branch A's item
        response = self.client.get(item_url)
        self.assertEqual(len(response.data), 0)

        # 5. HQ Admin list items: should see ALL items
        self.client.force_authenticate(user=self.org_admin)
        response = self.client.get(item_url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], item_a_id)

        # 6. HQ Admin attempts to create item in decentralized mode (should be blocked)
        response = self.client.post(item_url, {
            "name": "Pepsi Max 1L",
            "category": cat_a_id
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # policy permission blocks HQ admin writes

    def test_uniqueness_validations(self):
        """
        Test that manual serializer check handles unique category/item name/code duplication.
        """
        self.org.item_creation_policy = Organization.Policy.ORG_ADMIN
        self.org.save()

        # Create category
        cat = ItemCategory.objects.create(
            organization=self.org,
            name="Juices",
            code="CAT-JUICE"
        )

        # Direct creation of item
        Item.objects.create(
            organization=self.org,
            category=cat,
            name="Nestle Orange 1L",
            code="JUICE-01"
        )

        self.client.force_authenticate(user=self.org_admin)
        item_url = reverse('item-list')

        # Try to create duplicate name
        response = self.client.post(item_url, {
            "name": "Nestle Orange 1L",
            "category": cat.id,
            "code": "JUICE-02"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("An item with name 'Nestle Orange 1L' already exists globally.", str(response.data))

        # Try to create duplicate code
        response = self.client.post(item_url, {
            "name": "Nestle Apple 1L",
            "category": cat.id,
            "code": "JUICE-01"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("An item with code 'JUICE-01' already exists globally.", str(response.data))

    def test_sequential_code_generation(self):
        """
        Test category and item sequential code triggers correctly.
        """
        # Under Centralized
        self.org.item_creation_policy = Organization.Policy.ORG_ADMIN
        self.org.save()

        # Category seq code
        cat1 = ItemCategory.objects.create(organization=self.org, name="A")
        cat2 = ItemCategory.objects.create(organization=self.org, name="B")
        self.assertEqual(cat1.code, "CAT-0001")
        self.assertEqual(cat2.code, "CAT-0002")

        # Item seq code
        item1 = Item.objects.create(organization=self.org, category=cat1, name="Item A")
        item2 = Item.objects.create(organization=self.org, category=cat1, name="Item B")
        self.assertEqual(item1.code, "ITEM-0001")
        self.assertEqual(item2.code, "ITEM-0002")

    def test_item_optimistic_locking(self):
        self.org.item_creation_policy = Organization.Policy.ORG_ADMIN
        self.org.save()

        cat = ItemCategory.objects.create(organization=self.org, name="Juices")
        item = Item.objects.create(organization=self.org, category=cat, name="Lays Masala", code="LAYS-01")
        self.assertEqual(item.version, 1)

        detail_url = reverse('item-detail', kwargs={'pk': item.id})
        self.client.force_authenticate(user=self.org_admin)

        # 1. Update with mismatching version -> expect 409 Conflict
        response = self.client.put(detail_url, {
            "name": "Updated Lays Max",
            "category": cat.id,
            "version": 99
        })
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        item.refresh_from_db()
        self.assertEqual(item.name, "Lays Masala")
        self.assertEqual(item.version, 1)

        # 2. Update with matching version -> expect 200 OK
        response = self.client.put(detail_url, {
            "name": "Updated Lays Max",
            "category": cat.id,
            "version": 1
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.name, "Updated Lays Max")
        self.assertEqual(item.version, 2)

        # 3. Update without version -> expect success (backward compatibility)
        response = self.client.put(detail_url, {
            "name": "Updated No Version Lays",
            "category": cat.id
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.name, "Updated No Version Lays")
        self.assertEqual(item.version, 3)

