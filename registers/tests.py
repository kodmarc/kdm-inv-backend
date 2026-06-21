from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from organizations.models import Organization, Branch
from items.models import Item, ItemCategory
from companies.models import Company
from .models import (
    OrderBooker, Salesman, Party, AccountOpening,
    SalesInvoice, PurchaseInvoice, JournalEntry, JournalItem
)

User = get_user_model()

class RegistersAPITests(APITestCase):
    def setUp(self):
        # Setup Organizations
        self.org_a = Organization.objects.create(org_id='orga', name='Org A')
        self.org_b = Organization.objects.create(org_id='orgb', name='Org B')

        # Setup Branches
        self.branch_a1 = Branch.objects.create(organization=self.org_a, name='Branch A1', slug='branch-a1')
        self.branch_a2 = Branch.objects.create(organization=self.org_a, name='Branch A2', slug='branch-a2')
        self.branch_b = Branch.objects.create(organization=self.org_b, name='Branch B', slug='branch-b')

        # Setup Users
        self.admin_a = User.objects.create_user(
            username='admin_a', password='pwd', organization=self.org_a, role=User.Role.ORG_ADMIN
        )
        self.branch_admin_a1 = User.objects.create_user(
            username='ba_a1', password='pwd', organization=self.org_a, branch=self.branch_a1, role=User.Role.BRANCH_ADMIN
        )
        self.branch_admin_a2 = User.objects.create_user(
            username='ba_a2', password='pwd', organization=self.org_a, branch=self.branch_a2, role=User.Role.BRANCH_ADMIN
        )
        self.admin_b = User.objects.create_user(
            username='admin_b', password='pwd', organization=self.org_b, role=User.Role.ORG_ADMIN
        )

        # Setup Supporting Models for Transactions
        self.company = Company.objects.create(organization=self.org_a, name='Test Company', code='COMP-0001')
        self.category = ItemCategory.objects.create(organization=self.org_a, name='Test Category', code='CAT-0001')
        self.item = Item.objects.create(
            organization=self.org_a,
            company=self.company,
            category=self.category,
            name='Test Item',
            code='ITM-0001',
            current_stock=100.00,
            sales_rate=50.00,
            purchase_rate=40.00
        )

        self.account = AccountOpening.objects.create(organization=self.org_a, name='Sales Revenue Account')

        # Endpoints
        self.order_booker_url = reverse('order-booker-list')
        self.salesman_url = reverse('salesman-list')
        self.party_url = reverse('party-list')
        self.account_url = reverse('account-list')
        self.sales_invoice_url = reverse('sales-invoice-list')
        self.purchase_invoice_url = reverse('purchase-invoice-list')

    def test_deletion_blocked_across_all_registers_and_invoices(self):
        self.client.force_authenticate(user=self.admin_a)

        # 1. Order Booker
        ob = OrderBooker.objects.create(organization=self.org_a, name="OB 1", contact_no="123")
        url = reverse('order-booker-detail', kwargs={'pk': ob.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 2. Salesman
        sm = Salesman.objects.create(organization=self.org_a, name="SM 1", contact_no="123")
        url = reverse('salesman-detail', kwargs={'pk': sm.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 3. Party
        pty = Party.objects.create(organization=self.org_a, name="Pty 1", contact_no="123", is_party=True)
        url = reverse('party-detail', kwargs={'pk': pty.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 4. AccountOpening
        acc = AccountOpening.objects.create(organization=self.org_a, name="Acc 1")
        url = reverse('account-detail', kwargs={'pk': acc.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)



        # 6. Sales Invoice
        sales_inv = SalesInvoice.objects.create(
            organization=self.org_a, company=self.company, date='2026-06-19',
            party=pty, account=self.account, net_amount=100.00
        )
        url = reverse('sales-invoice-detail', kwargs={'pk': sales_inv.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 7. Purchase Invoice
        pur_inv = PurchaseInvoice.objects.create(
            organization=self.org_a, company=self.company, date='2026-06-19',
            supplier=pty, account=self.account, net_amount=100.00
        )
        url = reverse('purchase-invoice-detail', kwargs={'pk': pur_inv.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_scoping_and_isolation(self):
        # Create as branch admin a1 -> should auto-assign branch_a1
        self.client.force_authenticate(user=self.branch_admin_a1)
        payload = {"name": "Test Contact", "contact_no": "03001234567", "is_party": True}
        response = self.client.post(self.party_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["branch"], self.branch_a1.slug)

        # Fetch as branch admin a1 -> should see it
        response = self.client.get(self.party_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Test Contact")

        # Fetch as branch admin a2 -> should NOT see it (isolation)
        self.client.force_authenticate(user=self.branch_admin_a2)
        response = self.client.get(self.party_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # Fetch as tenant B admin -> should NOT see it (multi-tenant isolation)
        self.client.force_authenticate(user=self.admin_b)
        response = self.client.get(self.party_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # HQ admin A can see it
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.get(self.party_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_party_role_validation(self):
        self.client.force_authenticate(user=self.admin_a)
        
        # Post party without setting any role -> Fail
        payload = {"name": "No Role Party", "contact_no": "111"}
        response = self.client.post(self.party_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

        # Post party with is_party=True -> Success
        payload["is_party"] = True
        response = self.client.post(self.party_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_uniqueness_validations(self):
        # Create party under branch A1
        self.client.force_authenticate(user=self.branch_admin_a1)
        payload = {"name": "Unique Party", "contact_no": "111", "is_party": True}
        response = self.client.post(self.party_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Attempt to create duplicate name in branch A1 -> fail
        response = self.client.post(self.party_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

        # Create duplicate name in branch A2 -> success
        self.client.force_authenticate(user=self.branch_admin_a2)
        response = self.client.post(self.party_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_account_opening_auto_code_generation(self):
        self.client.force_authenticate(user=self.branch_admin_a1)
        
        # Create Account 1
        payload1 = {"name": "Cash Ledger A", "opening_balance": "100.00"}
        response1 = self.client.post(self.account_url, payload1)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response1.data["code"], "ACC-0001")
        self.assertEqual(response1.data["balance"], "100.00")

        # Create Account 2
        payload2 = {"name": "Sales Ledger A"}
        response2 = self.client.post(self.account_url, payload2)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.data["code"], "ACC-0002")

        # Test code uniqueness validation when manually provided
        payload3 = {"name": "Duplicate Code", "code": "ACC-0001"}
        response3 = self.client.post(self.account_url, payload3)
        self.assertEqual(response3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response3.data)



    def test_sales_invoice_creation_stock_and_ledger_impact(self):
        self.client.force_authenticate(user=self.admin_a)

        # Set up a customer party
        party = Party.objects.create(organization=self.org_a, name="Customer Party", contact_no="0300", is_party=True)

        payload = {
            "date": "2026-06-19",
            "status": "pending",
            "party": party.id,
            "company": self.company.id,
            "account": self.account.id,
            "discount": "10.00",
            "net_amount": "90.00",
            "ntn": "1234567-8",
            "gst_no": "12-34-5678-901-23",
            "credit_limit": "5000.00",
            "credit_days": 15,
            "balance_amount": "200.00",
            "line_items": [
                {
                    "item": self.item.id,
                    "carton": "0.00",
                    "pcs": "2.00",
                    "rate": "50.00",
                    "amount": "100.00",
                    "s_tax_amount": "0.00",
                    "f_tax_amount": "0.00",
                    "gross_amount": "100.00",
                    "to_rate": "0.00",
                    "to_amount": "0.00",
                    "net_amount": "100.00"
                }
            ]
        }

        # Post invoice
        response = self.client.post(self.sales_invoice_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 1. Verify item stock decreased (100 - 2 = 98)
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, 98.00)

        # 2. Verify Party balance increased by invoice net_amount (90)
        party.refresh_from_db()
        self.assertEqual(party.balance_amount, 90.00)

        # 3. Verify ledger account balance increased
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 90.00)

        # 4. Verify snapshot values are saved correctly
        invoice = SalesInvoice.objects.get(id=response.data["id"])
        self.assertEqual(invoice.ntn, "1234567-8")
        self.assertEqual(invoice.gst_no, "12-34-5678-901-23")
        self.assertEqual(invoice.credit_limit, 5000.00)
        self.assertEqual(invoice.credit_days, 15)
        self.assertEqual(invoice.balance_amount, 200.00)

        # 5. Verify journal entries were created
        self.assertEqual(JournalEntry.objects.filter(sales_invoice=invoice).count(), 1)
        entry = JournalEntry.objects.get(sales_invoice=invoice)
        self.assertEqual(entry.reference, invoice.sale_code)
        
        # Verify balanced items
        items = list(JournalItem.objects.filter(entry=entry))
        self.assertEqual(len(items), 2)
        debit_item = next(it for it in items if it.debit > 0)
        credit_item = next(it for it in items if it.credit > 0)
        self.assertEqual(debit_item.party, party)
        self.assertEqual(debit_item.debit, 90.00)
        self.assertEqual(credit_item.account, self.account)
        self.assertEqual(credit_item.credit, 90.00)

    def test_sales_invoice_oversold_validation(self):
        self.client.force_authenticate(user=self.admin_a)
        party = Party.objects.create(organization=self.org_a, name="Customer", contact_no="0300", is_party=True)

        # Attempt to sell 150 units when stock is 100
        payload = {
            "date": "2026-06-19",
            "status": "pending",
            "party": party.id,
            "company": self.company.id,
            "account": self.account.id,
            "discount": "0.00",
            "net_amount": "7500.00",
            "line_items": [
                {
                    "item": self.item.id,
                    "carton": "0.00",
                    "pcs": "150.00",
                    "rate": "50.00",
                    "amount": "7500.00",
                    "net_amount": "7500.00"
                }
            ]
        }

        response = self.client.post(self.sales_invoice_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, 100.00)  # Verify no stock change

    def test_purchase_invoice_creation_stock_and_ledger_impact(self):
        self.client.force_authenticate(user=self.admin_a)

        # Set up a supplier party
        supplier = Party.objects.create(organization=self.org_a, name="Supplier Party", contact_no="0300", is_supplier=True)

        payload = {
            "date": "2026-06-19",
            "status": "pending",
            "supplier": supplier.id,
            "company": self.company.id,
            "account": self.account.id,
            "s_tax": "0.00",
            "freight": "50.00",
            "adv_income_tax": "0.00",
            "net_amount": "450.00",
            "ntn": "8765432-1",
            "gst_no": "98-76-5432-109-87",
            "credit_limit": "8000.00",
            "credit_days": 30,
            "balance_amount": "400.00",
            "line_items": [
                {
                    "item": self.item.id,
                    "carton": "1.00",
                    "pcs": "10.00",
                    "rate": "40.00",
                    "amount": "400.00",
                    "discount_amount": "0.00",
                    "to_rate": "0.00",
                    "to_amount": "0.00",
                    "s_tax_rate": "0.00",
                    "s_tax_amount": "0.00",
                    "net_amount": "400.00"
                }
            ]
        }

        # Post invoice
        response = self.client.post(self.purchase_invoice_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 1. Verify item stock increased (100 + 10 = 110)
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, 110.00)

        # 2. Verify Supplier balance increased (450)
        supplier.refresh_from_db()
        self.assertEqual(supplier.balance_amount, 450.00)

        # 3. Verify ledger account balance increased
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 450.00)

        # 4. Verify snapshot values are saved correctly
        invoice = PurchaseInvoice.objects.get(id=response.data["id"])
        self.assertEqual(invoice.ntn, "8765432-1")
        self.assertEqual(invoice.gst_no, "98-76-5432-109-87")
        self.assertEqual(invoice.credit_limit, 8000.00)
        self.assertEqual(invoice.credit_days, 30)
        self.assertEqual(invoice.balance_amount, 400.00)

        # 5. Verify journal entries were created
        self.assertEqual(JournalEntry.objects.filter(purchase_invoice=invoice).count(), 1)
        entry = JournalEntry.objects.get(purchase_invoice=invoice)
        self.assertEqual(entry.reference, invoice.purchase_code)
        
        # Verify balanced items
        items = list(JournalItem.objects.filter(entry=entry))
        self.assertEqual(len(items), 2)
        debit_item = next(it for it in items if it.debit > 0)
        credit_item = next(it for it in items if it.credit > 0)
        self.assertEqual(debit_item.account, self.account)
        self.assertEqual(debit_item.debit, 450.00)
        self.assertEqual(credit_item.party, supplier)
        self.assertEqual(credit_item.credit, 450.00)

    def test_sales_invoice_change_status_ledger_impact(self):
        self.client.force_authenticate(user=self.admin_a)
        party = Party.objects.create(organization=self.org_a, name="Customer for Payment", contact_no="0300", is_party=True, balance_amount=0.00)
        
        # 1. Create a pending sales invoice
        invoice = SalesInvoice.objects.create(
            organization=self.org_a,
            party=party,
            company=self.company,
            account=self.account,
            date='2026-06-19',
            status='pending',
            net_amount=150.00
        )
        party.balance_amount += 150.00
        party.save()
        self.account.balance += 150.00
        self.account.save()
        
        # Create base sales invoice journal entry manually for this ORM-created invoice
        JournalEntry.objects.create(
            organization=self.org_a,
            date='2026-06-19',
            description="Sales Invoice test",
            reference=invoice.sale_code,
            sales_invoice=invoice
        )
        
        # Verify initial state
        self.assertEqual(party.balance_amount, 150.00)
        self.assertEqual(self.account.balance, 150.00)
        self.assertEqual(JournalEntry.objects.filter(sales_invoice=invoice).count(), 1)
        
        # 2. Change status to paid using action endpoint
        url = reverse('sales-invoice-change-status', kwargs={'pk': invoice.id})
        response = self.client.post(url, {"status": "paid"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Assert states
        invoice.refresh_from_db()
        party.refresh_from_db()
        self.account.refresh_from_db()
        
        self.assertEqual(invoice.status, 'paid')
        self.assertEqual(party.balance_amount, 0.00)  # Party balance reduced to 0
        self.assertEqual(self.account.balance, 150.00)  # Revenue account remains 150
        
        # Verify settlement journal entry exists
        self.assertEqual(JournalEntry.objects.filter(sales_invoice=invoice).count(), 2)
        pay_entry = JournalEntry.objects.get(sales_invoice=invoice, reference=f"PAY-{invoice.sale_code}")
        pay_items = list(JournalItem.objects.filter(entry=pay_entry))
        self.assertEqual(len(pay_items), 2)
        pay_debit = next(it for it in pay_items if it.debit > 0)
        pay_credit = next(it for it in pay_items if it.credit > 0)
        self.assertEqual(pay_debit.account, self.account)
        self.assertEqual(pay_debit.debit, 150.00)
        self.assertEqual(pay_credit.party, party)
        self.assertEqual(pay_credit.credit, 150.00)

        # 4. Change status back to pending using action endpoint
        response = self.client.post(url, {"status": "pending"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        invoice.refresh_from_db()
        party.refresh_from_db()
        self.assertEqual(invoice.status, 'pending')
        self.assertEqual(party.balance_amount, 150.00)  # Party balance increased back to 150
        
        # Verify settlement journal entry was deleted
        self.assertEqual(JournalEntry.objects.filter(sales_invoice=invoice).count(), 1)
        self.assertFalse(JournalEntry.objects.filter(sales_invoice=invoice, reference=f"PAY-{invoice.sale_code}").exists())

    def test_purchase_invoice_change_status_ledger_impact(self):
        self.client.force_authenticate(user=self.admin_a)
        supplier = Party.objects.create(organization=self.org_a, name="Supplier for Payment", contact_no="0300", is_supplier=True, balance_amount=0.00)
        
        # 1. Create a pending purchase invoice
        invoice = PurchaseInvoice.objects.create(
            organization=self.org_a,
            supplier=supplier,
            company=self.company,
            account=self.account,
            date='2026-06-19',
            status='pending',
            net_amount=250.00
        )
        supplier.balance_amount += 250.00
        supplier.save()
        self.account.balance += 250.00
        self.account.save()
        
        # Create base purchase invoice journal entry manually for this ORM-created invoice
        JournalEntry.objects.create(
            organization=self.org_a,
            date='2026-06-19',
            description="Purchase Invoice test",
            reference=invoice.purchase_code,
            purchase_invoice=invoice
        )
        
        # Verify initial state
        self.assertEqual(supplier.balance_amount, 250.00)
        self.assertEqual(self.account.balance, 250.00)
        self.assertEqual(JournalEntry.objects.filter(purchase_invoice=invoice).count(), 1)
        
        # 2. Change status using action endpoint
        url = reverse('purchase-invoice-change-status', kwargs={'pk': invoice.id})
        response = self.client.post(url, {"status": "paid"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Assert states
        invoice.refresh_from_db()
        supplier.refresh_from_db()
        self.account.refresh_from_db()
        
        self.assertEqual(invoice.status, 'paid')
        self.assertEqual(supplier.balance_amount, 0.00)  # Supplier balance reduced to 0
        self.assertEqual(self.account.balance, 250.00)  # Expense account remains 250
        
        # Verify settlement journal entry exists
        self.assertEqual(JournalEntry.objects.filter(purchase_invoice=invoice).count(), 2)
        pay_entry = JournalEntry.objects.get(purchase_invoice=invoice, reference=f"PAY-{invoice.purchase_code}")
        pay_items = list(JournalItem.objects.filter(entry=pay_entry))
        self.assertEqual(len(pay_items), 2)
        pay_debit = next(it for it in pay_items if it.debit > 0)
        pay_credit = next(it for it in pay_items if it.credit > 0)
        self.assertEqual(pay_debit.party, supplier)
        self.assertEqual(pay_debit.debit, 250.00)
        self.assertEqual(pay_credit.account, self.account)
        self.assertEqual(pay_credit.credit, 250.00)

        # 4. Change status back using action endpoint
        response = self.client.post(url, {"status": "pending"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        invoice.refresh_from_db()
        supplier.refresh_from_db()
        self.assertEqual(invoice.status, 'pending')
        self.assertEqual(supplier.balance_amount, 250.00)  # Supplier balance increased back to 250
        
        # Verify settlement journal entry was deleted
        self.assertEqual(JournalEntry.objects.filter(purchase_invoice=invoice).count(), 1)
        self.assertFalse(JournalEntry.objects.filter(purchase_invoice=invoice, reference=f"PAY-{invoice.purchase_code}").exists())

    def test_sales_invoice_download_pdf(self):
        self.client.force_authenticate(user=self.admin_a)
        party = Party.objects.create(organization=self.org_a, name="Customer for PDF", contact_no="0300", is_party=True)
        invoice = SalesInvoice.objects.create(
            organization=self.org_a,
            party=party,
            company=self.company,
            account=self.account,
            date='2026-06-19',
            status='pending',
            net_amount=150.00
        )
        
        # Test default/regular PDF download
        url = reverse('sales-invoice-download-pdf', kwargs={'pk': invoice.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))
        self.assertIn(f"Invoice_{invoice.sale_code}.pdf", response['Content-Disposition'])

        # Test booker PDF download
        response = self.client.get(url, {'type': 'booker'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # Test s_tax PDF download
        response = self.client.get(url, {'type': 's_tax'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_purchase_invoice_download_pdf(self):
        self.client.force_authenticate(user=self.admin_a)
        supplier = Party.objects.create(organization=self.org_a, name="Supplier for PDF", contact_no="0300", is_supplier=True)
        invoice = PurchaseInvoice.objects.create(
            organization=self.org_a,
            supplier=supplier,
            company=self.company,
            account=self.account,
            date='2026-06-19',
            status='pending',
            net_amount=250.00
        )
        
        url = reverse('purchase-invoice-download-pdf', kwargs={'pk': invoice.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))
        self.assertIn(f"Invoice_{invoice.purchase_code}.pdf", response['Content-Disposition'])

    def test_ledger_statement_endpoints(self):
        self.client.force_authenticate(user=self.admin_a)
        
        # Create a party
        party = Party.objects.create(organization=self.org_a, name="Statement Customer", contact_no="0300", is_party=True)
        
        # Create a journal entry manually for simplicity
        entry = JournalEntry.objects.create(
            organization=self.org_a,
            date="2026-06-20",
            description="Manual test entry",
            reference="TX-1001"
        )
        JournalItem.objects.create(entry=entry, party=party, debit=100.00, credit=0.00)
        JournalItem.objects.create(entry=entry, account=self.account, debit=0.00, credit=100.00)
        
        # Query party statement
        party_url = reverse('party-statement', kwargs={'pk': party.id})
        response = self.client.get(party_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['debit'], '100.00')
        self.assertEqual(response.data[0]['party_name'], "Statement Customer")
        
        # Query account statement
        account_url = reverse('account-statement', kwargs={'pk': self.account.id})
        response = self.client.get(account_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['credit'], '100.00')
        self.assertEqual(response.data[0]['account_name'], "Sales Revenue Account")

    def test_branch_sequence_locking_concurrency(self):
        from organizations.models import get_next_sequence_value, BranchSequence
        from django.db import connection

        # Reset sequences
        BranchSequence.objects.all().delete()

        if connection.vendor == 'sqlite':
            # SQLite does not support concurrent select_for_update locks across threads,
            # so we verify the sequence counts sequentially.
            results = []
            for _ in range(10):
                results.append(get_next_sequence_value(self.org_a, self.branch_a1, 'SAL'))
        else:
            # Under production databases (PostgreSQL/MySQL), execute concurrent thread check
            import concurrent.futures
            connection.close()

            def worker():
                from django.db import connection
                val = get_next_sequence_value(self.org_a, self.branch_a1, 'SAL')
                connection.close()
                return val

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(worker) for _ in range(10)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verify we got unique sequence numbers from 1 to 10
        self.assertEqual(len(results), 10)
        self.assertEqual(set(results), set(range(1, 11)))

        # Verify sequential count for another sequence type
        v1 = get_next_sequence_value(self.org_a, self.branch_a1, 'PUR')
        v2 = get_next_sequence_value(self.org_a, self.branch_a1, 'PUR')
        self.assertEqual(v1, 1)
        self.assertEqual(v2, 2)




