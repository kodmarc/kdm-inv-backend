import uuid
from django.db import models
from organizations.models import Organization, Branch, get_next_sequence_value

class OrderBooker(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='order_bookers')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='order_bookers', null=True, blank=True)
    name = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=50)
    email = models.EmailField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_orderbooker_name'
            ),
            models.UniqueConstraint(
                fields=['branch', 'name'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_orderbooker_name'
            ),
        ]

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"{self.name} ({self.contact_no}{branch_info})"


class Salesman(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='salesmen')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='salesmen', null=True, blank=True)
    name = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=50)
    email = models.EmailField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Salesmen'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_salesman_name'
            ),
            models.UniqueConstraint(
                fields=['branch', 'name'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_salesman_name'
            ),
        ]

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"{self.name} ({self.contact_no}{branch_info})"


class Party(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='parties')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='parties', null=True, blank=True)
    name = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=50)
    email = models.EmailField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    is_supplier = models.BooleanField(default=False)
    is_party = models.BooleanField(default=False)
    
    ntn = models.CharField(max_length=100, blank=True, null=True)
    gst_no = models.CharField(max_length=100, blank=True, null=True)
    
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Parties'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_party_name'
            ),
            models.UniqueConstraint(
                fields=['branch', 'name'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_party_name'
            ),
        ]

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        roles = []
        if self.is_supplier: roles.append("Supplier")
        if self.is_party: roles.append("Party")
        role_info = f" [{', '.join(roles)}]" if roles else ""
        return f"{self.name} ({self.contact_no}{branch_info}){role_info}"


class AccountOpening(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='ledger_accounts')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='ledger_accounts', null=True, blank=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_account_name'
            ),
            models.UniqueConstraint(
                fields=['branch', 'name'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_account_name'
            ),
            models.UniqueConstraint(
                fields=['organization', 'code'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_account_code'
            ),
            models.UniqueConstraint(
                fields=['branch', 'code'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_account_code'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = "ACC"
            next_val = get_next_sequence_value(self.organization, self.branch, prefix)
            self.code = f"{prefix}-{next_val:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"{self.name} ({self.code}{branch_info})"


class SalesInvoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='sales_invoices')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='sales_invoices', null=True, blank=True)
    sale_code = models.CharField(max_length=50, blank=True)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='sales_invoices')
    order_booker = models.ForeignKey(OrderBooker, on_delete=models.PROTECT, related_name='sales_invoices', null=True, blank=True)
    salesman = models.ForeignKey(Salesman, on_delete=models.PROTECT, related_name='sales_invoices', null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='sales_invoices')
    account = models.ForeignKey(AccountOpening, on_delete=models.PROTECT, related_name='sales_invoices')
    
    ntn = models.CharField(max_length=100, blank=True, null=True)
    gst_no = models.CharField(max_length=100, blank=True, null=True)
    credit_days = models.IntegerField(default=0)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'sale_code'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_sales_invoice_code'
            ),
            models.UniqueConstraint(
                fields=['branch', 'sale_code'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_sales_invoice_code'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.sale_code:
            prefix = "SAL"
            next_val = get_next_sequence_value(self.organization, self.branch, prefix)
            self.sale_code = f"{prefix}-{next_val:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"{self.sale_code} - {self.party.name} ({self.net_amount}{branch_info})"


class SalesInvoiceLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='line_items')
    item = models.ForeignKey('items.Item', on_delete=models.PROTECT, related_name='sales_invoice_items')
    
    bal_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    carton = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pcs = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    s_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    f_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    to_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    to_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.invoice.sale_code} - Item: {self.item.name} - Qty: {self.pcs}"


class PurchaseInvoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='purchase_invoices')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='purchase_invoices', null=True, blank=True)
    purchase_code = models.CharField(max_length=50, blank=True)
    date = models.DateField()
    supplier = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='purchase_invoices')
    account = models.ForeignKey(AccountOpening, on_delete=models.PROTECT, related_name='purchase_invoices')
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='purchase_invoices')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True, null=True)
    s_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    ntn = models.CharField(max_length=100, blank=True, null=True)
    gst_no = models.CharField(max_length=100, blank=True, null=True)
    credit_days = models.IntegerField(default=0)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    freight = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    adv_income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'purchase_code'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_purchase_invoice_code'
            ),
            models.UniqueConstraint(
                fields=['branch', 'purchase_code'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_purchase_invoice_code'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.purchase_code:
            prefix = "PUR"
            next_val = get_next_sequence_value(self.organization, self.branch, prefix)
            self.purchase_code = f"{prefix}-{next_val:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"{self.purchase_code} - Supplier: {self.supplier.name} ({self.net_amount}{branch_info})"


class PurchaseInvoiceLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='line_items')
    item = models.ForeignKey('items.Item', on_delete=models.PROTECT, related_name='purchase_invoice_items')
    
    carton = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pcs = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    to_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    to_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    s_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    s_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.invoice.purchase_code} - Item: {self.item.name} - Qty: {self.pcs}"


class JournalEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='journal_entries')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='journal_entries', null=True, blank=True)
    date = models.DateField()
    description = models.CharField(max_length=500, blank=True)
    reference = models.CharField(max_length=255, blank=True)
    
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')
    purchase_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')
    purchase_return = models.ForeignKey('PurchaseReturn', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')
    damage_return = models.ForeignKey('DamageReturn', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')
    sales_return = models.ForeignKey('SalesReturn', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')  # ✅ Added
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"JV-{self.reference or self.id.hex[:6]} ({self.date}{branch_info})"


class JournalItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='items')
    
    account = models.ForeignKey(AccountOpening, on_delete=models.PROTECT, related_name='journal_items', null=True, blank=True)
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='journal_items', null=True, blank=True)
    
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    description = models.CharField(max_length=500, blank=True)

    def __str__(self):
        target = self.account.name if self.account else (self.party.name if self.party else "None")
        return f"{self.entry} | {target} | Debit: {self.debit} | Credit: {self.credit}"


# ============== PURCHASE RETURN ==============

class PurchaseReturn(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]
    RETURN_TYPE_CHOICES = [
        ('normal', 'Normal'),
        ('damage', 'Damage'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='purchase_returns')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='purchase_returns', null=True, blank=True)
    purchase_return_code = models.CharField(max_length=50, blank=True)
    date = models.DateField()
    party_inv_no = models.CharField(max_length=100, blank=True, null=True)
    supplier = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='purchase_returns')
    account = models.ForeignKey(AccountOpening, on_delete=models.PROTECT, related_name='purchase_returns')
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='purchase_returns')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    return_type = models.CharField(max_length=20, choices=RETURN_TYPE_CHOICES, default='normal')  # ✅ Normal/Damage
    
    remarks = models.TextField(blank=True, null=True)
    s_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    ntn = models.CharField(max_length=100, blank=True, null=True)
    gst_no = models.CharField(max_length=100, blank=True, null=True)
    credit_days = models.IntegerField(default=0)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    freight = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    adv_income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
         indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'return_type']),
            models.Index(fields=['company', '-created_at']),
        ]
         constraints = [
            models.UniqueConstraint(
                fields=['organization', 'purchase_return_code'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_purchase_return_code'
            ),
            models.UniqueConstraint(
                fields=['branch', 'purchase_return_code'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_purchase_return_code'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.purchase_return_code:
            prefix = "PRN"
            next_val = get_next_sequence_value(self.organization, self.branch, prefix)
            self.purchase_return_code = f"{prefix}-{next_val:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"{self.purchase_return_code} - Supplier: {self.supplier.name} ({self.net_amount}{branch_info})"


class PurchaseReturnLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_return = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, related_name='line_items')
    item = models.ForeignKey('items.Item', on_delete=models.PROTECT, related_name='purchase_return_items')
    
    carton = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pcs = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    to_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    to_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    s_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    s_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.purchase_return.purchase_return_code} - Item: {self.item.name} - Qty: {self.pcs}"


# ============== DAMAGE RETURN (Supplier Damage Returns) ==============

class DamageReturn(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='damage_returns')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='damage_returns', null=True, blank=True)
    damage_return_code = models.CharField(max_length=50, blank=True)
    date = models.DateField()
    party_inv_no = models.CharField(max_length=100, blank=True, null=True)
    supplier = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='damage_returns')
    account = models.ForeignKey(AccountOpening, on_delete=models.PROTECT, related_name='damage_returns')
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='damage_returns')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True, null=True)
    s_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    ntn = models.CharField(max_length=100, blank=True, null=True)
    gst_no = models.CharField(max_length=100, blank=True, null=True)
    credit_days = models.IntegerField(default=0)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'damage_return_code'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_damage_return_code'
            ),
            models.UniqueConstraint(
                fields=['branch', 'damage_return_code'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_damage_return_code'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.damage_return_code:
            prefix = "DRN"
            next_val = get_next_sequence_value(self.organization, self.branch, prefix)
            self.damage_return_code = f"{prefix}-{next_val:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"{self.damage_return_code} - Supplier: {self.supplier.name} ({self.net_amount}{branch_info})"


class DamageReturnLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    damage_return = models.ForeignKey(DamageReturn, on_delete=models.CASCADE, related_name='line_items')
    item = models.ForeignKey('items.Item', on_delete=models.PROTECT, related_name='damage_return_items')
    
    carton = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pcs = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    s_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    s_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.damage_return.damage_return_code} - Item: {self.item.name} - Qty: {self.pcs}"


# ============== SALES RETURN (Customer Returns - Replaces DamageReceiving) ==============

class SalesReturn(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]
    RETURN_TYPE_CHOICES = [
        ('normal', 'Normal'),
        ('damage', 'Damage'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='sales_returns')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='sales_returns', null=True, blank=True)
    sales_return_code = models.CharField(max_length=50, blank=True)
    date = models.DateField()
    salesman = models.ForeignKey(Salesman, on_delete=models.PROTECT, related_name='sales_returns', null=True, blank=True)
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='sales_returns')
    account = models.ForeignKey(AccountOpening, on_delete=models.PROTECT, related_name='sales_returns')
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='sales_returns')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    return_type = models.CharField(max_length=20, choices=RETURN_TYPE_CHOICES, default='normal')  # ✅ Normal/Damage
    
    remarks = models.TextField(blank=True, null=True)
    s_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    ntn = models.CharField(max_length=100, blank=True, null=True)
    gst_no = models.CharField(max_length=100, blank=True, null=True)
    credit_days = models.IntegerField(default=0)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
          indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'return_type']),
            models.Index(fields=['company', '-created_at']),
        ]
          
          constraints = [
            models.UniqueConstraint(
                fields=['organization', 'sales_return_code'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_sales_return_code'
            ),
            models.UniqueConstraint(
                fields=['branch', 'sales_return_code'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_sales_return_code'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.sales_return_code:
            prefix = "SRN"
            next_val = get_next_sequence_value(self.organization, self.branch, prefix)
            self.sales_return_code = f"{prefix}-{next_val:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"{self.sales_return_code} - Party: {self.party.name} ({self.net_amount}{branch_info})"


class SalesReturnLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sales_return = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, related_name='line_items')
    item = models.ForeignKey('items.Item', on_delete=models.PROTECT, related_name='sales_return_items')
    
    manual_code = models.CharField(max_length=50, blank=True, null=True)
    carton = models.DecimalField(max_digits=12, decimal_places=2, default=0.00) 
    issue_units = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pcs = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    s_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    s_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.sales_return.sales_return_code} - Item: {self.item.name} - Qty: {self.pcs}"