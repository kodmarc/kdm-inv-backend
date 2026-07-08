# Data Models

All primary keys are UUIDs generated at creation time. All models use `created_at` (auto_now_add) and where noted `updated_at` (auto_now) timestamps.

---

## accounts app

**User** extends Django's AbstractUser.

- `organization` — FK to Organization, nullable (null for platform superadmins)
- `branch` — FK to Branch, nullable (null for HQ roles)
- `role` — CharField, choices: ORG_ADMIN / ORG_USER / BRANCH_ADMIN / USER / KPO
- `username` — CharField, not globally unique; uniqueness is scoped to org or branch via database constraints

Username uniqueness is enforced at the database level: HQ-role usernames must be unique per organization, branch-role usernames must be unique per branch.

---

## organizations app

**Organization**

- `org_id` — unique identifier chosen at signup (alphanumeric, min 5 chars, at least one letter and one number), always stored lowercase
- `name` — display name
- `company_creation_policy` — ORG_ADMIN or BRANCH_ADMIN, default ORG_ADMIN
- `item_creation_policy` — ORG_ADMIN or BRANCH_ADMIN, default ORG_ADMIN

**Branch**

- `organization` — FK to Organization
- `name` — display name
- `slug` — used in URLs (e.g. `/branch/karachi/companies`), unique per organization

**BranchSequence**

Used by the auto-code generation system. Tracks the next invoice/account code number per organization/branch/type combination.

- `organization` — FK to Organization
- `branch` — FK to Branch, nullable (null for org-level sequences)
- `sequence_type` — e.g. `'PUR'`, `'SAL'`, `'ACC'`
- `next_val` — IntegerField, incremented atomically on each use

A unique constraint ensures one sequence per (org or branch) + type combination.

---

## companies app

**Company**

- `organization` — FK to Organization
- `branch` — FK to Branch, nullable
- `name` — CharField
- `code` — CharField, auto-generated via BranchSequence if not provided (format: COM-0001)

---

## items app

**ItemCategory**

- `organization` — FK to Organization
- `branch` — FK to Branch, nullable
- `name` — CharField
- `code` — auto-generated (format: CAT-0001)
- `description` — optional text

**Item**

- `organization` — FK to Organization
- `branch` — FK to Branch, nullable
- `category` — FK to ItemCategory
- `company` — FK to Company, optional
- `name` — CharField
- `code` — auto-generated (format: ITM-0001)
- `sku` — optional
- `pack` — integer, carton-to-pieces ratio (default 1)
- `grammage` — optional description of weight/size
- `purchase_rate`, `sales_rate` — DecimalField
- `purchase_tax`, `sales_tax`, `federal_tax` — percentage DecimalFields
- `discount_slab_qty`, `discount_slab_rate` — optional slab pricing
- `min_stock`, `max_stock` — optional thresholds
- `current_stock` — DecimalField, updated on every invoice/return creation
- `damaged_stock` — DecimalField, updated on damage transactions
- `is_active` — BooleanField

---

## registers app

**OrderBooker**

- `organization`, `branch` (nullable)
- `name`, `contact_no`, `email`, `is_active`

**Salesman**

- `organization`, `branch` (nullable)
- `name`, `contact_no`, `email`, `is_active`

**Party**

Represents both suppliers and customers. A single contact can be both.

- `organization`, `branch` (nullable)
- `name`, `contact_no`, `email`, `is_active`
- `is_supplier` — BooleanField
- `is_party` — BooleanField (true for customers/debtors)
- `ntn`, `gst_no` — tax identifiers, optional
- `credit_limit`, `balance_amount` — DecimalFields, balance updated on invoice creation/deletion
- `credit_days` — IntegerField (informational, stored on snapshot at invoice time)

**AccountOpening**

The ledger account registry. Each account tracks a running balance.

- `organization`, `branch` (nullable)
- `name`, `code` — code auto-generated (format: ACC-0001)
- `opening_balance`, `balance` — DecimalFields
- `is_active` — BooleanField

**SalesInvoice**

- `organization`, `branch` (nullable)
- `sale_code` — auto-generated (format: SAL-0001)
- `date` — DateField
- `status` — pending or paid
- `party` — FK to Party
- `order_booker`, `salesman` — optional FKs
- `account` — FK to AccountOpening (the cash/bank account receiving payment)
- `company` — FK to Company
- `remarks` — optional
- `discount`, `net_amount` — DecimalFields
- Snapshot fields copied from Party at creation time: `ntn`, `gst_no`, `credit_days`, `credit_limit`, `balance_amount`

**SalesInvoiceLineItem**

- `invoice` — FK to SalesInvoice (CASCADE delete)
- `item` — FK to Item
- `carton`, `pcs` — quantity fields
- `rate`, `amount` — unit price and gross amount
- `s_tax_amount`, `f_tax_amount` — sales tax and federal tax amounts
- `to_rate`, `to_amount` — trade offer / discount rate and amount
- `gross_amount`, `net_amount` — computed totals

**PurchaseInvoice**

- `organization`, `branch` (nullable)
- `purchase_code` — auto-generated (format: PUR-0001)
- `date` — DateField
- `status` — pending or paid
- `supplier` — FK to Party (must have `is_supplier=True`)
- `account` — FK to AccountOpening
- `company` — FK to Company
- `remarks`, `s_tax`, `freight`, `adv_income_tax`, `net_amount` — summary fields
- Snapshot fields from supplier: `ntn`, `gst_no`, `credit_days`, `credit_limit`, `balance_amount`

**PurchaseInvoiceLineItem**

- `invoice` — FK to PurchaseInvoice (CASCADE)
- `item` — FK to Item
- `carton`, `pcs`, `rate`, `amount`
- `discount_amount`, `to_rate`, `to_amount`
- `s_tax_rate`, `s_tax_amount`, `net_amount`

**PurchaseReturn / PurchaseReturnLineItem**

Mirror of PurchaseInvoice/LineItem but with a `purchase_return_code` (format: RET-0001) and a `party_inv_no` field for referencing the original supplier invoice number. Stock is decremented on return creation.

**DamageReturn / DamageReturnLineItem**

Records damaged goods returned to the supplier. Has a `damage_return_code` (format: DMR-0001). Decrements `damaged_stock` on the item.

**DamageReceiving / DamageReceivingLineItem**

Records damaged goods received from customers. Has a `damage_receiving_code` (format: DMR-REC). Increments `damaged_stock` on the item.

**JournalEntry**

Auto-created by the serializer on every invoice/return save. Never created directly by the user.

- `organization`, `branch` (nullable)
- `date`, `description`, `reference`
- Optional FKs to the originating document: `sales_invoice`, `purchase_invoice`, `purchase_return`, `damage_return`, `damage_receiving`

**JournalItem**

Each line on a JournalEntry. Represents one debit or credit posting.

- `entry` — FK to JournalEntry (CASCADE)
- `account` — FK to AccountOpening, nullable
- `party` — FK to Party, nullable
- `debit`, `credit` — DecimalFields
- `description` — CharField

Either `account` or `party` is set per line, not both.
