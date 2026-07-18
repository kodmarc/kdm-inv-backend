from rest_framework import serializers
from django.db import transaction
from organizations.models import Branch
from items.models import Item
from companies.models import Company
from .models import (
    OrderBooker, Salesman, Party, AccountOpening, 
    SalesInvoice, SalesInvoiceLineItem, 
    PurchaseInvoice, PurchaseInvoiceLineItem, 
    JournalEntry, JournalItem, 
    PurchaseReturn, PurchaseReturnLineItem, 
    DamageReturn, DamageReturnLineItem, 
    SalesReturn, SalesReturnLineItem  # ✅ Only these - no DamageReceiving
)

class OrderBookerSerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = OrderBooker
        fields = ['id', 'name', 'contact_no', 'email', 'is_active', 'branch', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            self.fields['branch'].queryset = Branch.objects.filter(
                organization=request.user.organization
            )

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        user = request.user
        org = user.organization

        name = attrs.get('name', self.instance.name if self.instance else None)
        contact_no = attrs.get('contact_no', self.instance.contact_no if self.instance else None)
        branch = attrs.get('branch', self.instance.branch if self.instance else None)

        if not self.instance:
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                attrs['branch'] = user.branch
                branch = user.branch
        else:
            if 'branch' in attrs and attrs['branch'] != self.instance.branch:
                raise serializers.ValidationError({"branch": "Branch mapping cannot be changed after creation."})

        if name:
            attrs['name'] = name.strip()
        if contact_no:
            attrs['contact_no'] = contact_no.strip()

        qs = OrderBooker.objects.filter(organization=org)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if branch:
            if qs.filter(branch=branch, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"An order booker with name '{attrs['name']}' already exists in branch '{branch.name}'."})
        else:
            if qs.filter(branch__isnull=True, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"An order booker with name '{attrs['name']}' already exists globally."})

        return attrs


class SalesmanSerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Salesman
        fields = ['id', 'name', 'contact_no', 'email', 'is_active', 'branch', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            self.fields['branch'].queryset = Branch.objects.filter(
                organization=request.user.organization
            )

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        user = request.user
        org = user.organization

        name = attrs.get('name', self.instance.name if self.instance else None)
        contact_no = attrs.get('contact_no', self.instance.contact_no if self.instance else None)
        branch = attrs.get('branch', self.instance.branch if self.instance else None)

        if not self.instance:
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                attrs['branch'] = user.branch
                branch = user.branch
        else:
            if 'branch' in attrs and attrs['branch'] != self.instance.branch:
                raise serializers.ValidationError({"branch": "Branch mapping cannot be changed after creation."})

        if name:
            attrs['name'] = name.strip()
        if contact_no:
            attrs['contact_no'] = contact_no.strip()

        qs = Salesman.objects.filter(organization=org)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if branch:
            if qs.filter(branch=branch, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"A salesman with name '{attrs['name']}' already exists in branch '{branch.name}'."})
        else:
            if qs.filter(branch__isnull=True, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"A salesman with name '{attrs['name']}' already exists globally."})

        return attrs


class PartySerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Party
        fields = [
            'id', 'name', 'contact_no', 'email', 'is_active', 'branch',
            'is_supplier', 'is_party', 'ntn', 'gst_no',
            'credit_limit', 'balance_amount',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'balance_amount', 'created_at', 'updated_at']
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            self.fields['branch'].queryset = Branch.objects.filter(
                organization=request.user.organization
            )

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        user = request.user
        org = user.organization

        name = attrs.get('name', self.instance.name if self.instance else None)
        contact_no = attrs.get('contact_no', self.instance.contact_no if self.instance else None)
        branch = attrs.get('branch', self.instance.branch if self.instance else None)

        if not self.instance:
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                attrs['branch'] = user.branch
                branch = user.branch
        else:
            if 'branch' in attrs and attrs['branch'] != self.instance.branch:
                raise serializers.ValidationError({"branch": "Branch mapping cannot be changed after creation."})

        is_supplier = attrs.get('is_supplier', self.instance.is_supplier if self.instance else False)
        is_party = attrs.get('is_party', self.instance.is_party if self.instance else False)
        if not is_supplier and not is_party:
            raise serializers.ValidationError("At least one role must be selected (Is Supplier or Is Party).")

        if name:
            attrs['name'] = name.strip()
        if contact_no:
            attrs['contact_no'] = contact_no.strip()

        qs = Party.objects.filter(organization=org)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if branch:
            if qs.filter(branch=branch, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"A contact with name '{attrs['name']}' already exists in branch '{branch.name}'."})
        else:
            if qs.filter(branch__isnull=True, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"A contact with name '{attrs['name']}' already exists globally."})

        return attrs


class AccountOpeningSerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )
    code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = AccountOpening
        fields = [
            'id', 'name', 'code', 'opening_balance', 
            'balance', 'is_active', 'branch', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at']
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            self.fields['branch'].queryset = Branch.objects.filter(
                organization=request.user.organization
            )

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication credentials were not provided.")

        user = request.user
        org = user.organization

        name = attrs.get('name', self.instance.name if self.instance else None)
        code = attrs.get('code', self.instance.code if self.instance else None)
        branch = attrs.get('branch', self.instance.branch if self.instance else None)

        if not self.instance:
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                attrs['branch'] = user.branch
                branch = user.branch
            attrs['balance'] = attrs.get('opening_balance', 0.00)
        else:
            if 'branch' in attrs and attrs['branch'] != self.instance.branch:
                raise serializers.ValidationError({"branch": "Branch mapping cannot be changed after creation."})

        if name:
            attrs['name'] = name.strip()
        if code:
            attrs['code'] = code.strip()

        qs = AccountOpening.objects.filter(organization=org)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if branch:
            if qs.filter(branch=branch, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"An account with name '{attrs['name']}' already exists in branch '{branch.name}'."})
        else:
            if qs.filter(branch__isnull=True, name__iexact=attrs['name']).exists():
                raise serializers.ValidationError({"name": f"An account with name '{attrs['name']}' already exists globally."})

        if code:
            if branch:
                if qs.filter(branch=branch, code__iexact=attrs['code']).exists():
                    raise serializers.ValidationError({"code": f"An account with code '{attrs['code']}' already exists in this branch."})
            else:
                if qs.filter(branch__isnull=True, code__iexact=attrs['code']).exists():
                    raise serializers.ValidationError({"code": f"An account with code '{attrs['code']}' already exists globally."})

        return attrs


# ============== SALES INVOICE ==============

class SalesInvoiceLineItemSerializer(serializers.ModelSerializer):
    item_name = serializers.ReadOnlyField(source='item.name')
    item_code = serializers.ReadOnlyField(source='item.code')

    class Meta:
        model = SalesInvoiceLineItem
        fields = [
            'id', 'item', 'item_name', 'item_code', 'bal_qty',
            'carton', 'pcs', 'rate', 'amount',
            's_tax_amount', 'f_tax_amount', 'gross_amount',
            'to_rate', 'to_amount', 'net_amount'
        ]


class SalesInvoiceSerializer(serializers.ModelSerializer):
    line_items = SalesInvoiceLineItemSerializer(many=True)
    party_name = serializers.ReadOnlyField(source='party.name')
    company_name = serializers.ReadOnlyField(source='company.name')
    account_name = serializers.ReadOnlyField(source='account.name')
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = SalesInvoice
        fields = [
            'id', 'sale_code', 'date', 'status', 'party', 'party_name',
            'order_booker', 'salesman', 'remarks', 'company', 'company_name',
            'account', 'account_name', 'ntn', 'gst_no', 'credit_days',
            'credit_limit', 'balance_amount',
            'discount', 'net_amount', 'branch', 'line_items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sale_code', 'created_at', 'updated_at']

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        org = user.organization
        branch = attrs.get('branch', self.instance.branch if self.instance else None)

        if not self.instance:
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                attrs['branch'] = user.branch
                branch = user.branch
            attrs['organization'] = org

        party = attrs.get('party')
        if party and party.organization != org:
            raise serializers.ValidationError({"party": "Party does not belong to this organization."})
        if party and not party.is_party:
            raise serializers.ValidationError({"party": "Selected contact is not designated as a Party."})

        company = attrs.get('company')
        if company and company.organization != org:
            raise serializers.ValidationError({"company": "Company does not belong to this organization."})

        items_stock_deltas = {}
        if self.instance:
            for old_line in self.instance.line_items.all():
                items_stock_deltas[old_line.item.id] = old_line.pcs

        line_items_data = attrs.get('line_items', [])
        for line in line_items_data:
            item = line['item']
            pcs_needed = line['pcs']
            available = item.current_stock + items_stock_deltas.get(item.id, 0)
            if available < pcs_needed:
                raise serializers.ValidationError(
                    f"Insufficient stock for item '{item.name}'. Available: {available}, Required: {pcs_needed}."
                )

        return attrs

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items')
        
        with transaction.atomic():
            party = validated_data['party']
            validated_data['ntn'] = validated_data.get('ntn') or party.ntn
            validated_data['gst_no'] = validated_data.get('gst_no') or party.gst_no
            validated_data['credit_limit'] = validated_data.get('credit_limit') if validated_data.get('credit_limit') is not None else party.credit_limit
            validated_data['credit_days'] = validated_data.get('credit_days') if validated_data.get('credit_days') is not None else 0
            validated_data['balance_amount'] = validated_data.get('balance_amount') if validated_data.get('balance_amount') is not None else party.balance_amount

            invoice = SalesInvoice.objects.create(**validated_data)

            for item_data in line_items_data:
                item = item_data['item']
                item_data['bal_qty'] = item.current_stock
                SalesInvoiceLineItem.objects.create(invoice=invoice, **item_data)
                
                item.current_stock -= item_data['pcs']
                item.save()

            if invoice.status == 'pending':
                party.balance_amount += invoice.net_amount
                party.save()

            invoice.account.balance += invoice.net_amount
            invoice.account.save()

            sales_entry = JournalEntry.objects.create(
                organization=invoice.organization,
                branch=invoice.branch,
                date=invoice.date,
                description=f"Sales Invoice {invoice.sale_code} - Party: {invoice.party.name}",
                reference=invoice.sale_code,
                sales_invoice=invoice
            )
            JournalItem.objects.create(
                entry=sales_entry,
                party=invoice.party,
                debit=invoice.net_amount,
                credit=0.00,
                description=f"Accounts Receivable - Invoice {invoice.sale_code}"
            )
            JournalItem.objects.create(
                entry=sales_entry,
                account=invoice.account,
                debit=0.00,
                credit=invoice.net_amount,
                description=f"Sales Revenue - Invoice {invoice.sale_code}"
            )

            if invoice.status == 'paid':
                pay_entry = JournalEntry.objects.create(
                    organization=invoice.organization,
                    branch=invoice.branch,
                    date=invoice.date,
                    description=f"Payment Receipt for Invoice {invoice.sale_code}",
                    reference=f"PAY-{invoice.sale_code}",
                    sales_invoice=invoice
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=invoice.account,
                    debit=invoice.net_amount,
                    credit=0.00,
                    description=f"Cash Receipt - Invoice {invoice.sale_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=invoice.party,
                    debit=0.00,
                    credit=invoice.net_amount,
                    description=f"Accounts Receivable Settlement - Invoice {invoice.sale_code}"
                )

            return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)

        with transaction.atomic():
            JournalEntry.objects.filter(sales_invoice=instance).delete()

            for old_line in instance.line_items.all():
                item = old_line.item
                item.current_stock += old_line.pcs
                item.save()

            old_party = instance.party
            if instance.status == 'pending':
                old_party.balance_amount -= instance.net_amount
                old_party.save()

            old_account = instance.account
            old_account.balance -= instance.net_amount
            old_account.save()

            instance.line_items.all().delete()

            instance.party = validated_data.get('party', instance.party)
            instance.date = validated_data.get('date', instance.date)
            instance.status = validated_data.get('status', instance.status)
            instance.order_booker = validated_data.get('order_booker', instance.order_booker)
            instance.salesman = validated_data.get('salesman', instance.salesman)
            instance.remarks = validated_data.get('remarks', instance.remarks)
            instance.company = validated_data.get('company', instance.company)
            instance.account = validated_data.get('account', instance.account)
            instance.discount = validated_data.get('discount', instance.discount)
            instance.net_amount = validated_data.get('net_amount', instance.net_amount)

            new_party = instance.party
            party_changed = 'party' in validated_data
            
            instance.ntn = validated_data.get('ntn') if 'ntn' in validated_data else (new_party.ntn if party_changed else instance.ntn)
            instance.gst_no = validated_data.get('gst_no') if 'gst_no' in validated_data else (new_party.gst_no if party_changed else instance.gst_no)
            instance.credit_limit = validated_data.get('credit_limit') if 'credit_limit' in validated_data else (new_party.credit_limit if party_changed else instance.credit_limit)
            instance.credit_days = validated_data.get('credit_days') if 'credit_days' in validated_data else (0 if party_changed else instance.credit_days)
            instance.balance_amount = validated_data.get('balance_amount') if 'balance_amount' in validated_data else (new_party.balance_amount if party_changed else instance.balance_amount)

            instance.save()

            for item_data in line_items_data:
                item = item_data['item']
                item_data['bal_qty'] = item.current_stock
                SalesInvoiceLineItem.objects.create(invoice=instance, **item_data)

                item.current_stock -= item_data['pcs']
                item.save()

            if instance.status == 'pending':
                new_party.balance_amount += instance.net_amount
                new_party.save()

            instance.account.balance += instance.net_amount
            instance.account.save()

            sales_entry = JournalEntry.objects.create(
                organization=instance.organization,
                branch=instance.branch,
                date=instance.date,
                description=f"Sales Invoice {instance.sale_code} - Party: {instance.party.name}",
                reference=instance.sale_code,
                sales_invoice=instance
            )
            JournalItem.objects.create(
                entry=sales_entry,
                party=instance.party,
                debit=instance.net_amount,
                credit=0.00,
                description=f"Accounts Receivable - Invoice {instance.sale_code}"
            )
            JournalItem.objects.create(
                entry=sales_entry,
                account=instance.account,
                debit=0.00,
                credit=instance.net_amount,
                description=f"Sales Revenue - Invoice {instance.sale_code}"
            )

            if instance.status == 'paid':
                pay_entry = JournalEntry.objects.create(
                    organization=instance.organization,
                    branch=instance.branch,
                    date=instance.date,
                    description=f"Payment Receipt for Invoice {instance.sale_code}",
                    reference=f"PAY-{instance.sale_code}",
                    sales_invoice=instance
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=instance.account,
                    debit=instance.net_amount,
                    credit=0.00,
                    description=f"Cash Receipt - Invoice {instance.sale_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=instance.party,
                    debit=0.00,
                    credit=instance.net_amount,
                    description=f"Accounts Receivable Settlement - Invoice {instance.sale_code}"
                )

            return instance


# ============== PURCHASE INVOICE ==============

class PurchaseInvoiceLineItemSerializer(serializers.ModelSerializer):
    item_name = serializers.ReadOnlyField(source='item.name')
    item_code = serializers.ReadOnlyField(source='item.code')

    class Meta:
        model = PurchaseInvoiceLineItem
        fields = [
            'id', 'item', 'item_name', 'item_code',
            'carton', 'pcs', 'rate', 'amount',
            'discount_amount', 'to_rate', 'to_amount',
            's_tax_rate', 's_tax_amount', 'net_amount'
        ]


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    line_items = PurchaseInvoiceLineItemSerializer(many=True)
    supplier_name = serializers.ReadOnlyField(source='supplier.name')
    company_name = serializers.ReadOnlyField(source='company.name')
    account_name = serializers.ReadOnlyField(source='account.name')
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = PurchaseInvoice
        fields = [
            'id', 'purchase_code', 'date', 'supplier', 'supplier_name',
            'account', 'account_name', 'company', 'company_name', 'status',
            'remarks', 's_tax', 'freight', 'adv_income_tax', 'net_amount',
            'ntn', 'gst_no', 'credit_days', 'credit_limit', 'balance_amount',
            'branch', 'line_items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'purchase_code', 'created_at', 'updated_at']

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        org = user.organization

        if not self.instance:
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                attrs['branch'] = user.branch
            attrs['organization'] = org

        supplier = attrs.get('supplier')
        if supplier and supplier.organization != org:
            raise serializers.ValidationError({"supplier": "Supplier does not belong to this organization."})
        if supplier and not supplier.is_supplier:
            raise serializers.ValidationError({"supplier": "Selected contact is not designated as a Supplier."})

        company = attrs.get('company')
        if company and company.organization != org:
            raise serializers.ValidationError({"company": "Company does not belong to this organization."})

        return attrs

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items')

        with transaction.atomic():
            supplier = validated_data['supplier']
            validated_data['ntn'] = validated_data.get('ntn') or supplier.ntn
            validated_data['gst_no'] = validated_data.get('gst_no') or supplier.gst_no
            validated_data['credit_limit'] = validated_data.get('credit_limit') if validated_data.get('credit_limit') is not None else supplier.credit_limit
            validated_data['credit_days'] = validated_data.get('credit_days') if validated_data.get('credit_days') is not None else 0
            validated_data['balance_amount'] = validated_data.get('balance_amount') if validated_data.get('balance_amount') is not None else supplier.balance_amount

            invoice = PurchaseInvoice.objects.create(**validated_data)

            for item_data in line_items_data:
                item = item_data['item']
                PurchaseInvoiceLineItem.objects.create(invoice=invoice, **item_data)

                item.current_stock += item_data['pcs']
                item.save()

            supplier = invoice.supplier
            if invoice.status == 'pending':
                supplier.balance_amount += invoice.net_amount
                supplier.save()

            invoice.account.balance += invoice.net_amount
            invoice.account.save()

            purchase_entry = JournalEntry.objects.create(
                organization=invoice.organization,
                branch=invoice.branch,
                date=invoice.date,
                description=f"Purchase Invoice {invoice.purchase_code} - Supplier: {invoice.supplier.name}",
                reference=invoice.purchase_code,
                purchase_invoice=invoice
            )
            JournalItem.objects.create(
                entry=purchase_entry,
                account=invoice.account,
                debit=invoice.net_amount,
                credit=0.00,
                description=f"Purchase Expense - Invoice {invoice.purchase_code}"
            )
            JournalItem.objects.create(
                entry=purchase_entry,
                party=invoice.supplier,
                debit=0.00,
                credit=invoice.net_amount,
                description=f"Accounts Payable - Invoice {invoice.purchase_code}"
            )

            if invoice.status == 'paid':
                pay_entry = JournalEntry.objects.create(
                    organization=invoice.organization,
                    branch=invoice.branch,
                    date=invoice.date,
                    description=f"Payment Settlement for Purchase {invoice.purchase_code}",
                    reference=f"PAY-{invoice.purchase_code}",
                    purchase_invoice=invoice
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=invoice.supplier,
                    debit=invoice.net_amount,
                    credit=0.00,
                    description=f"Accounts Payable Settlement - Invoice {invoice.purchase_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=invoice.account,
                    debit=0.00,
                    credit=invoice.net_amount,
                    description=f"Cash Paid - Invoice {invoice.purchase_code}"
                )

            return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)

        with transaction.atomic():
            JournalEntry.objects.filter(purchase_invoice=instance).delete()

            for old_line in instance.line_items.all():
                item = old_line.item
                item.current_stock -= old_line.pcs
                item.save()

            old_supplier = instance.supplier
            if instance.status == 'pending':
                old_supplier.balance_amount -= instance.net_amount
                old_supplier.save()

            old_account = instance.account
            old_account.balance -= instance.net_amount
            old_account.save()

            instance.line_items.all().delete()

            instance.supplier = validated_data.get('supplier', instance.supplier)
            instance.date = validated_data.get('date', instance.date)
            instance.status = validated_data.get('status', instance.status)
            instance.remarks = validated_data.get('remarks', instance.remarks)
            instance.company = validated_data.get('company', instance.company)
            instance.account = validated_data.get('account', instance.account)
            instance.s_tax = validated_data.get('s_tax', instance.s_tax)
            instance.freight = validated_data.get('freight', instance.freight)
            instance.adv_income_tax = validated_data.get('adv_income_tax', instance.adv_income_tax)
            instance.net_amount = validated_data.get('net_amount', instance.net_amount)

            new_supplier = instance.supplier
            supplier_changed = 'supplier' in validated_data
            
            instance.ntn = validated_data.get('ntn') if 'ntn' in validated_data else (new_supplier.ntn if supplier_changed else instance.ntn)
            instance.gst_no = validated_data.get('gst_no') if 'gst_no' in validated_data else (new_supplier.gst_no if supplier_changed else instance.gst_no)
            instance.credit_limit = validated_data.get('credit_limit') if 'credit_limit' in validated_data else (new_supplier.credit_limit if supplier_changed else instance.credit_limit)
            instance.credit_days = validated_data.get('credit_days') if 'credit_days' in validated_data else (0 if supplier_changed else instance.credit_days)
            instance.balance_amount = validated_data.get('balance_amount') if 'balance_amount' in validated_data else (new_supplier.balance_amount if supplier_changed else instance.balance_amount)

            instance.save()

            for item_data in line_items_data:
                item = item_data['item']
                PurchaseInvoiceLineItem.objects.create(invoice=instance, **item_data)

                item.current_stock += item_data['pcs']
                item.save()

            new_supplier = instance.supplier
            if instance.status == 'pending':
                new_supplier.balance_amount += instance.net_amount
                new_supplier.save()

            instance.account.balance += instance.net_amount
            instance.account.save()

            purchase_entry = JournalEntry.objects.create(
                organization=instance.organization,
                branch=instance.branch,
                date=instance.date,
                description=f"Purchase Invoice {instance.purchase_code} - Supplier: {instance.supplier.name}",
                reference=instance.purchase_code,
                purchase_invoice=instance
            )
            JournalItem.objects.create(
                entry=purchase_entry,
                account=instance.account,
                debit=instance.net_amount,
                credit=0.00,
                description=f"Purchase Expense - Invoice {instance.purchase_code}"
            )
            JournalItem.objects.create(
                entry=purchase_entry,
                party=instance.supplier,
                debit=0.00,
                credit=instance.net_amount,
                description=f"Accounts Payable - Invoice {instance.purchase_code}"
            )

            if instance.status == 'paid':
                pay_entry = JournalEntry.objects.create(
                    organization=instance.organization,
                    branch=instance.branch,
                    date=instance.date,
                    description=f"Payment Settlement for Purchase {instance.purchase_code}",
                    reference=f"PAY-{instance.purchase_code}",
                    purchase_invoice=instance
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=instance.supplier,
                    debit=instance.net_amount,
                    credit=0.00,
                    description=f"Accounts Payable Settlement - Invoice {instance.purchase_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=instance.account,
                    debit=0.00,
                    credit=instance.net_amount,
                    description=f"Cash Paid - Invoice {instance.purchase_code}"
                )

            return instance


# ============== PURCHASE RETURN ==============

class PurchaseReturnLineItemSerializer(serializers.ModelSerializer):
    item_name = serializers.ReadOnlyField(source='item.name')
    item_code = serializers.ReadOnlyField(source='item.code')

    class Meta:
        model = PurchaseReturnLineItem
        fields = [
            'id', 'item', 'item_name', 'item_code',
            'carton', 'pcs', 'rate', 'amount',
            'discount_amount', 'to_rate', 'to_amount',
            's_tax_rate', 's_tax_amount', 'net_amount'
        ]


class PurchaseReturnSerializer(serializers.ModelSerializer):
    line_items = PurchaseReturnLineItemSerializer(many=True)
    supplier_name = serializers.ReadOnlyField(source='supplier.name')
    company_name = serializers.ReadOnlyField(source='company.name')
    account_name = serializers.ReadOnlyField(source='account.name')
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = PurchaseReturn
        fields = [
            'id', 'purchase_return_code', 'date', 'party_inv_no', 'supplier', 'supplier_name',
            'account', 'account_name', 'company', 'company_name', 'status',
            'return_type',  # ✅ Normal/Damage field
            'remarks', 's_tax', 'freight', 'adv_income_tax', 'net_amount',
            'ntn', 'gst_no', 'credit_days', 'credit_limit', 'balance_amount',
            'branch', 'line_items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'purchase_return_code', 'created_at', 'updated_at']

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        org = user.organization

        if not self.instance:
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                attrs['branch'] = user.branch
            attrs['organization'] = org

        supplier = attrs.get('supplier')
        if supplier and supplier.organization != org:
            raise serializers.ValidationError({"supplier": "Supplier does not belong to this organization."})
        if supplier and not supplier.is_supplier:
            raise serializers.ValidationError({"supplier": "Selected contact is not designated as a Supplier."})

        company = attrs.get('company')
        if company and company.organization != org:
            raise serializers.ValidationError({"company": "Company does not belong to this organization."})

        return attrs

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items')

        with transaction.atomic():
            supplier = validated_data['supplier']
            validated_data['ntn'] = validated_data.get('ntn') or supplier.ntn
            validated_data['gst_no'] = validated_data.get('gst_no') or supplier.gst_no
            validated_data['credit_limit'] = validated_data.get('credit_limit') if validated_data.get('credit_limit') is not None else supplier.credit_limit
            validated_data['credit_days'] = validated_data.get('credit_days') if validated_data.get('credit_days') is not None else 0
            validated_data['balance_amount'] = validated_data.get('balance_amount') if validated_data.get('balance_amount') is not None else supplier.balance_amount

            purchase_return = PurchaseReturn.objects.create(**validated_data)

            for item_data in line_items_data:
                item = item_data['item']
                PurchaseReturnLineItem.objects.create(purchase_return=purchase_return, **item_data)

                item.current_stock -= item_data['pcs']
                item.save()

            supplier = purchase_return.supplier
            if purchase_return.status == 'pending':
                supplier.balance_amount -= purchase_return.net_amount
                supplier.save()

            purchase_return.account.balance -= purchase_return.net_amount
            purchase_return.account.save()

            return_entry = JournalEntry.objects.create(
                organization=purchase_return.organization,
                branch=purchase_return.branch,
                date=purchase_return.date,
                description=f"Purchase Return {purchase_return.purchase_return_code} - Supplier: {purchase_return.supplier.name}",
                reference=purchase_return.purchase_return_code,
                purchase_return=purchase_return
            )
            JournalItem.objects.create(
                entry=return_entry,
                party=purchase_return.supplier,
                debit=purchase_return.net_amount,
                credit=0.00,
                description=f"Accounts Payable Reduced - Return {purchase_return.purchase_return_code}"
            )
            JournalItem.objects.create(
                entry=return_entry,
                account=purchase_return.account,
                debit=0.00,
                credit=purchase_return.net_amount,
                description=f"Purchase Return - Return {purchase_return.purchase_return_code}"
            )

            if purchase_return.status == 'paid':
                pay_entry = JournalEntry.objects.create(
                    organization=purchase_return.organization,
                    branch=purchase_return.branch,
                    date=purchase_return.date,
                    description=f"Cash Refund for Purchase Return {purchase_return.purchase_return_code}",
                    reference=f"REF-{purchase_return.purchase_return_code}",
                    purchase_return=purchase_return
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=purchase_return.account,
                    debit=purchase_return.net_amount,
                    credit=0.00,
                    description=f"Cash Refund Received - Return {purchase_return.purchase_return_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=purchase_return.supplier,
                    debit=0.00,
                    credit=purchase_return.net_amount,
                    description=f"Supplier Refund Settlement - Return {purchase_return.purchase_return_code}"
                )

            return purchase_return

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)

        with transaction.atomic():
            JournalEntry.objects.filter(purchase_return=instance).delete()

            for old_line in instance.line_items.all():
                item = old_line.item
                item.current_stock += old_line.pcs
                item.save()

            old_supplier = instance.supplier
            if instance.status == 'pending':
                old_supplier.balance_amount += instance.net_amount
                old_supplier.save()

            old_account = instance.account
            old_account.balance += instance.net_amount
            old_account.save()

            instance.line_items.all().delete()

            instance.supplier = validated_data.get('supplier', instance.supplier)
            instance.date = validated_data.get('date', instance.date)
            instance.status = validated_data.get('status', instance.status)
            instance.remarks = validated_data.get('remarks', instance.remarks)
            instance.company = validated_data.get('company', instance.company)
            instance.account = validated_data.get('account', instance.account)
            instance.s_tax = validated_data.get('s_tax', instance.s_tax)
            instance.freight = validated_data.get('freight', instance.freight)
            instance.adv_income_tax = validated_data.get('adv_income_tax', instance.adv_income_tax)
            instance.net_amount = validated_data.get('net_amount', instance.net_amount)
            instance.party_inv_no = validated_data.get('party_inv_no', instance.party_inv_no)
            instance.return_type = validated_data.get('return_type', instance.return_type)

            new_supplier = instance.supplier
            supplier_changed = 'supplier' in validated_data
            
            instance.ntn = validated_data.get('ntn') if 'ntn' in validated_data else (new_supplier.ntn if supplier_changed else instance.ntn)
            instance.gst_no = validated_data.get('gst_no') if 'gst_no' in validated_data else (new_supplier.gst_no if supplier_changed else instance.gst_no)
            instance.credit_limit = validated_data.get('credit_limit') if 'credit_limit' in validated_data else (new_supplier.credit_limit if supplier_changed else instance.credit_limit)
            instance.credit_days = validated_data.get('credit_days') if 'credit_days' in validated_data else (0 if supplier_changed else instance.credit_days)
            instance.balance_amount = validated_data.get('balance_amount') if 'balance_amount' in validated_data else (new_supplier.balance_amount if supplier_changed else instance.balance_amount)

            instance.save()

            if line_items_data is not None:
                for item_data in line_items_data:
                    item = item_data['item']
                    PurchaseReturnLineItem.objects.create(purchase_return=instance, **item_data)

                    item.current_stock -= item_data['pcs']
                    item.save()

            new_supplier = instance.supplier
            if instance.status == 'pending':
                new_supplier.balance_amount -= instance.net_amount
                new_supplier.save()

            instance.account.balance -= instance.net_amount
            instance.account.save()

            return_entry = JournalEntry.objects.create(
                organization=instance.organization,
                branch=instance.branch,
                date=instance.date,
                description=f"Purchase Return {instance.purchase_return_code} - Supplier: {instance.supplier.name}",
                reference=instance.purchase_return_code,
                purchase_return=instance
            )
            JournalItem.objects.create(
                entry=return_entry,
                party=instance.supplier,
                debit=instance.net_amount,
                credit=0.00,
                description=f"Accounts Payable Reduced - Return {instance.purchase_return_code}"
            )
            JournalItem.objects.create(
                entry=return_entry,
                account=instance.account,
                debit=0.00,
                credit=instance.net_amount,
                description=f"Purchase Return - Return {instance.purchase_return_code}"
            )

            if instance.status == 'paid':
                pay_entry = JournalEntry.objects.create(
                    organization=instance.organization,
                    branch=instance.branch,
                    date=instance.date,
                    description=f"Cash Refund for Purchase Return {instance.purchase_return_code}",
                    reference=f"REF-{instance.purchase_return_code}",
                    purchase_return=instance
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=instance.account,
                    debit=instance.net_amount,
                    credit=0.00,
                    description=f"Cash Refund Received - Return {instance.purchase_return_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=instance.supplier,
                    debit=0.00,
                    credit=instance.net_amount,
                    description=f"Supplier Refund Settlement - Return {instance.purchase_return_code}"
                )

            return instance


# ============== DAMAGE RETURN ==============

class DamageReturnLineItemSerializer(serializers.ModelSerializer):
    item_name = serializers.ReadOnlyField(source='item.name')
    item_code = serializers.ReadOnlyField(source='item.code')

    class Meta:
        model = DamageReturnLineItem
        fields = [
            'id', 'item', 'item_name', 'item_code',
            'carton', 'pcs', 'rate', 'amount',
            's_tax_rate', 's_tax_amount', 'net_amount'
        ]


class DamageReturnSerializer(serializers.ModelSerializer):
    line_items = DamageReturnLineItemSerializer(many=True)
    supplier_name = serializers.ReadOnlyField(source='supplier.name')
    company_name = serializers.ReadOnlyField(source='company.name')
    account_name = serializers.ReadOnlyField(source='account.name')
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = DamageReturn
        fields = [
            'id', 'damage_return_code', 'date', 'party_inv_no', 'supplier', 'supplier_name',
            'account', 'account_name', 'company', 'company_name', 'status',
            'remarks', 's_tax', 'net_amount',
            'ntn', 'gst_no', 'credit_days', 'credit_limit', 'balance_amount',
            'branch', 'line_items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'damage_return_code', 'created_at', 'updated_at']

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        org = user.organization

        if not self.instance:
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                attrs['branch'] = user.branch
            attrs['organization'] = org

        supplier = attrs.get('supplier')
        if supplier and supplier.organization != org:
            raise serializers.ValidationError({"supplier": "Supplier does not belong to this organization."})
        if supplier and not supplier.is_supplier:
            raise serializers.ValidationError({"supplier": "Selected contact is not designated as a Supplier."})

        company = attrs.get('company')
        if company and company.organization != org:
            raise serializers.ValidationError({"company": "Company does not belong to this organization."})

        return attrs

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items')

        with transaction.atomic():
            supplier = validated_data['supplier']
            validated_data['ntn'] = validated_data.get('ntn') or supplier.ntn
            validated_data['gst_no'] = validated_data.get('gst_no') or supplier.gst_no
            validated_data['credit_limit'] = validated_data.get('credit_limit') if validated_data.get('credit_limit') is not None else supplier.credit_limit
            validated_data['credit_days'] = validated_data.get('credit_days') if validated_data.get('credit_days') is not None else 0
            validated_data['balance_amount'] = validated_data.get('balance_amount') if validated_data.get('balance_amount') is not None else supplier.balance_amount

            damage_return = DamageReturn.objects.create(**validated_data)

            for item_data in line_items_data:
                item = item_data['item']
                DamageReturnLineItem.objects.create(damage_return=damage_return, **item_data)

                item.damaged_stock -= item_data['pcs']
                item.save()

            supplier = damage_return.supplier
            if damage_return.status == 'pending':
                supplier.balance_amount -= damage_return.net_amount
                supplier.save()

            damage_return.account.balance -= damage_return.net_amount
            damage_return.account.save()

            return_entry = JournalEntry.objects.create(
                organization=damage_return.organization,
                branch=damage_return.branch,
                date=damage_return.date,
                description=f"Damage Return {damage_return.damage_return_code} - Supplier: {damage_return.supplier.name}",
                reference=damage_return.damage_return_code,
                damage_return=damage_return
            )
            JournalItem.objects.create(
                entry=return_entry,
                party=damage_return.supplier,
                debit=damage_return.net_amount,
                credit=0.00,
                description=f"Accounts Payable Reduced (Damage) - Return {damage_return.damage_return_code}"
            )
            JournalItem.objects.create(
                entry=return_entry,
                account=damage_return.account,
                debit=0.00,
                credit=damage_return.net_amount,
                description=f"Damage Return - Return {damage_return.damage_return_code}"
            )

            if damage_return.status == 'paid':
                pay_entry = JournalEntry.objects.create(
                    organization=damage_return.organization,
                    branch=damage_return.branch,
                    date=damage_return.date,
                    description=f"Cash Refund for Damage Return {damage_return.damage_return_code}",
                    reference=f"REF-{damage_return.damage_return_code}",
                    damage_return=damage_return
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=damage_return.account,
                    debit=damage_return.net_amount,
                    credit=0.00,
                    description=f"Cash Refund Received (Damage) - Return {damage_return.damage_return_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=damage_return.supplier,
                    debit=0.00,
                    credit=damage_return.net_amount,
                    description=f"Supplier Refund Settlement (Damage) - Return {damage_return.damage_return_code}"
                )

            return damage_return

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)

        with transaction.atomic():
            JournalEntry.objects.filter(damage_return=instance).delete()

            for old_line in instance.line_items.all():
                item = old_line.item
                item.damaged_stock += old_line.pcs
                item.save()

            old_supplier = instance.supplier
            if instance.status == 'pending':
                old_supplier.balance_amount += instance.net_amount
                old_supplier.save()

            old_account = instance.account
            old_account.balance += instance.net_amount
            old_account.save()

            instance.line_items.all().delete()

            instance.supplier = validated_data.get('supplier', instance.supplier)
            instance.date = validated_data.get('date', instance.date)
            instance.status = validated_data.get('status', instance.status)
            instance.remarks = validated_data.get('remarks', instance.remarks)
            instance.company = validated_data.get('company', instance.company)
            instance.account = validated_data.get('account', instance.account)
            instance.s_tax = validated_data.get('s_tax', instance.s_tax)
            instance.net_amount = validated_data.get('net_amount', instance.net_amount)
            instance.party_inv_no = validated_data.get('party_inv_no', instance.party_inv_no)

            new_supplier = instance.supplier
            supplier_changed = 'supplier' in validated_data
            
            instance.ntn = validated_data.get('ntn') if 'ntn' in validated_data else (new_supplier.ntn if supplier_changed else instance.ntn)
            instance.gst_no = validated_data.get('gst_no') if 'gst_no' in validated_data else (new_supplier.gst_no if supplier_changed else instance.gst_no)
            instance.credit_limit = validated_data.get('credit_limit') if 'credit_limit' in validated_data else (new_supplier.credit_limit if supplier_changed else instance.credit_limit)
            instance.credit_days = validated_data.get('credit_days') if 'credit_days' in validated_data else (0 if supplier_changed else instance.credit_days)
            instance.balance_amount = validated_data.get('balance_amount') if 'balance_amount' in validated_data else (new_supplier.balance_amount if supplier_changed else instance.balance_amount)

            instance.save()

            if line_items_data is not None:
                for item_data in line_items_data:
                    item = item_data['item']
                    DamageReturnLineItem.objects.create(damage_return=instance, **item_data)

                    item.damaged_stock -= item_data['pcs']
                    item.save()

            new_supplier = instance.supplier
            if instance.status == 'pending':
                new_supplier.balance_amount -= instance.net_amount
                new_supplier.save()

            instance.account.balance -= instance.net_amount
            instance.account.save()

            return_entry = JournalEntry.objects.create(
                organization=instance.organization,
                branch=instance.branch,
                date=instance.date,
                description=f"Damage Return {instance.damage_return_code} - Supplier: {instance.supplier.name}",
                reference=instance.damage_return_code,
                damage_return=instance
            )
            JournalItem.objects.create(
                entry=return_entry,
                party=instance.supplier,
                debit=instance.net_amount,
                credit=0.00,
                description=f"Accounts Payable Reduced (Damage) - Return {instance.damage_return_code}"
            )
            JournalItem.objects.create(
                entry=return_entry,
                account=instance.account,
                debit=0.00,
                credit=instance.net_amount,
                description=f"Damage Return - Return {instance.damage_return_code}"
            )

            if instance.status == 'paid':
                pay_entry = JournalEntry.objects.create(
                    organization=instance.organization,
                    branch=instance.branch,
                    date=instance.date,
                    description=f"Cash Refund for Damage Return {instance.damage_return_code}",
                    reference=f"REF-{instance.damage_return_code}",
                    damage_return=instance
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=instance.account,
                    debit=instance.net_amount,
                    credit=0.00,
                    description=f"Cash Refund Received (Damage) - Return {instance.damage_return_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=instance.supplier,
                    debit=0.00,
                    credit=instance.net_amount,
                    description=f"Supplier Refund Settlement (Damage) - Return {instance.damage_return_code}"
                )

            return instance


# ============== JOURNAL ==============

class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = [   'id', 'date', 'description', 'reference',
            'sales_invoice', 'purchase_invoice', 'purchase_return', 'damage_return', 'sales_return', 'created_at'
        ]


class JournalItemSerializer(serializers.ModelSerializer):
    entry_details = JournalEntrySerializer(source='entry', read_only=True)
    account_name = serializers.ReadOnlyField(source='account.name')
    party_name = serializers.ReadOnlyField(source='party.name')

    class Meta:
        model = JournalItem
        fields = [
            'id', 'entry', 'entry_details', 'account', 'account_name',
            'party', 'party_name', 'debit', 'credit', 'description'
        ]


# ============== SALES RETURN ==============

class SalesReturnLineItemSerializer(serializers.ModelSerializer):
    item_name = serializers.ReadOnlyField(source='item.name')
    item_code = serializers.ReadOnlyField(source='item.code')

    class Meta:
        model = SalesReturnLineItem
        fields = [
            'id', 'item', 'item_name', 'item_code',
            'manual_code', 'issue_units', 'pcs', 'rate', 'amount',
            's_tax_rate', 's_tax_amount', 'gross_amount', 'net_amount'
        ]


class SalesReturnSerializer(serializers.ModelSerializer):
    line_items = SalesReturnLineItemSerializer(many=True)
    salesman_name = serializers.ReadOnlyField(source='salesman.name')
    party_name = serializers.ReadOnlyField(source='party.name')
    company_name = serializers.ReadOnlyField(source='company.name')
    account_name = serializers.ReadOnlyField(source='account.name')
    branch = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = SalesReturn
        fields = [
            'id', 'sales_return_code', 'date', 'salesman', 'salesman_name',
            'party', 'party_name', 'account', 'account_name', 'company', 'company_name',
            'status', 'return_type',  # ✅ Normal/Damage field
            'remarks', 's_tax', 'net_amount',
            'ntn', 'gst_no', 'credit_days', 'credit_limit', 'balance_amount',
            'branch', 'line_items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sales_return_code', 'created_at', 'updated_at']

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        org = user.organization

        if not self.instance:
            if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
                attrs['branch'] = user.branch
            attrs['organization'] = org

        party = attrs.get('party')
        if party and party.organization != org:
            raise serializers.ValidationError({"party": "Party does not belong to this organization."})
        if party and not party.is_party:
            raise serializers.ValidationError({"party": "Selected contact is not designated as a Customer/Party."})

        company = attrs.get('company')
        if company and company.organization != org:
            raise serializers.ValidationError({"company": "Company does not belong to this organization."})

        salesman = attrs.get('salesman')
        if salesman and salesman.organization != org:
            raise serializers.ValidationError({"salesman": "Salesman does not belong to this organization."})

        return attrs

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items')

        with transaction.atomic():
            party = validated_data['party']
            validated_data['ntn'] = validated_data.get('ntn') or party.ntn
            validated_data['gst_no'] = validated_data.get('gst_no') or party.gst_no
            validated_data['credit_limit'] = validated_data.get('credit_limit') if validated_data.get('credit_limit') is not None else party.credit_limit
            validated_data['credit_days'] = validated_data.get('credit_days') if validated_data.get('credit_days') is not None else 0
            validated_data['balance_amount'] = validated_data.get('balance_amount') if validated_data.get('balance_amount') is not None else party.balance_amount

            sales_return = SalesReturn.objects.create(**validated_data)

            for item_data in line_items_data:
                item = item_data['item']
                SalesReturnLineItem.objects.create(sales_return=sales_return, **item_data)

                item.current_stock += item_data['pcs']
                item.save()

            party = sales_return.party
            if sales_return.status == 'pending':
                party.balance_amount -= sales_return.net_amount
                party.save()

            sales_return.account.balance -= sales_return.net_amount
            sales_return.account.save()

            return_entry = JournalEntry.objects.create(
                organization=sales_return.organization,
                branch=sales_return.branch,
                date=sales_return.date,
                description=f"Sales Return {sales_return.sales_return_code} - Party: {sales_return.party.name}",
                reference=sales_return.sales_return_code,
                sales_invoice=None,
                purchase_invoice=None,
                purchase_return=None,
                damage_return=None,
                sales_return=None
            )
            JournalItem.objects.create(
                entry=return_entry,
                party=sales_return.party,
                debit=sales_return.net_amount,
                credit=0.00,
                description=f"Sales Return Adjustment - Return {sales_return.sales_return_code}"
            )
            JournalItem.objects.create(
                entry=return_entry,
                account=sales_return.account,
                debit=0.00,
                credit=sales_return.net_amount,
                description=f"Sales Return - Return {sales_return.sales_return_code}"
            )

            if sales_return.status == 'paid':
                pay_entry = JournalEntry.objects.create(
                    organization=sales_return.organization,
                    branch=sales_return.branch,
                    date=sales_return.date,
                    description=f"Cash Refund for Sales Return {sales_return.sales_return_code}",
                    reference=f"REF-{sales_return.sales_return_code}",
                    sales_invoice=None,
                    purchase_invoice=None,
                    purchase_return=None,
                    damage_return=None,
                    sales_return=None
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=sales_return.account,
                    debit=sales_return.net_amount,
                    credit=0.00,
                    description=f"Cash Refund Paid - Return {sales_return.sales_return_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=sales_return.party,
                    debit=0.00,
                    credit=sales_return.net_amount,
                    description=f"Customer Refund Settlement - Return {sales_return.sales_return_code}"
                )

            return sales_return

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)

        with transaction.atomic():
            JournalEntry.objects.filter(sales_invoice=instance).delete()

            for old_line in instance.line_items.all():
                item = old_line.item
                item.current_stock -= old_line.pcs
                item.save()

            old_party = instance.party
            if instance.status == 'pending':
                old_party.balance_amount += instance.net_amount
                old_party.save()

            old_account = instance.account
            old_account.balance += instance.net_amount
            old_account.save()

            instance.line_items.all().delete()

            instance.party = validated_data.get('party', instance.party)
            instance.salesman = validated_data.get('salesman', instance.salesman)
            instance.date = validated_data.get('date', instance.date)
            instance.status = validated_data.get('status', instance.status)
            instance.remarks = validated_data.get('remarks', instance.remarks)
            instance.company = validated_data.get('company', instance.company)
            instance.account = validated_data.get('account', instance.account)
            instance.s_tax = validated_data.get('s_tax', instance.s_tax)
            instance.net_amount = validated_data.get('net_amount', instance.net_amount)
            instance.return_type = validated_data.get('return_type', instance.return_type)

            new_party = instance.party
            party_changed = 'party' in validated_data

            instance.ntn = validated_data.get('ntn') if 'ntn' in validated_data else (new_party.ntn if party_changed else instance.ntn)
            instance.gst_no = validated_data.get('gst_no') if 'gst_no' in validated_data else (new_party.gst_no if party_changed else instance.gst_no)
            instance.credit_limit = validated_data.get('credit_limit') if 'credit_limit' in validated_data else (new_party.credit_limit if party_changed else instance.credit_limit)
            instance.credit_days = validated_data.get('credit_days') if 'credit_days' in validated_data else (0 if party_changed else instance.credit_days)
            instance.balance_amount = validated_data.get('balance_amount') if 'balance_amount' in validated_data else (new_party.balance_amount if party_changed else instance.balance_amount)

            instance.save()

            if line_items_data is not None:
                for item_data in line_items_data:
                    item = item_data['item']
                    SalesReturnLineItem.objects.create(sales_return=instance, **item_data)

                    item.current_stock += item_data['pcs']
                    item.save()

            new_party = instance.party
            if instance.status == 'pending':
                new_party.balance_amount -= instance.net_amount
                new_party.save()

            instance.account.balance -= instance.net_amount
            instance.account.save()

            return_entry = JournalEntry.objects.create(
                organization=instance.organization,
                branch=instance.branch,
                date=instance.date,
                description=f"Sales Return {instance.sales_return_code} - Party: {instance.party.name}",
                reference=instance.sales_return_code,
                sales_invoice=None,
                purchase_invoice=None,
                purchase_return=None,
                damage_return=None,
                sales_return=None
            )
            JournalItem.objects.create(
                entry=return_entry,
                party=instance.party,
                debit=instance.net_amount,
                credit=0.00,
                description=f"Sales Return Adjustment - Return {instance.sales_return_code}"
            )
            JournalItem.objects.create(
                entry=return_entry,
                account=instance.account,
                debit=0.00,
                credit=instance.net_amount,
                description=f"Sales Return - Return {instance.sales_return_code}"
            )

            if instance.status == 'paid':
                pay_entry = JournalEntry.objects.create(
                    organization=instance.organization,
                    branch=instance.branch,
                    date=instance.date,
                    description=f"Cash Refund for Sales Return {instance.sales_return_code}",
                    reference=f"REF-{instance.sales_return_code}",
                    sales_invoice=None,
                    purchase_invoice=None,
                    purchase_return=None,
                    damage_return=None,
                    sales_return=None
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=instance.account,
                    debit=instance.net_amount,
                    credit=0.00,
                    description=f"Cash Refund Paid - Return {instance.sales_return_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=instance.party,
                    debit=0.00,
                    credit=instance.net_amount,
                    description=f"Customer Refund Settlement - Return {instance.sales_return_code}"
                )

            return instance