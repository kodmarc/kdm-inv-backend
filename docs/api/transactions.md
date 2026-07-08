# API — Transactions

Transactions are the core of the system. There are five transaction types: purchase invoices, sales invoices, purchase returns, damage returns, and damage receivings. Every transaction creates journal entries automatically — there is no separate endpoint for journals.

All transaction endpoints require authentication. Branch-level roles can only create and view transactions for their own branch.

---

## Common Patterns

Before looking at individual endpoints, these patterns apply to all five transaction types.

**Snapshot fields.** When a transaction is created, fields like `ntn`, `gst_no`, `credit_limit`, and `balance_amount` are copied from the counterparty at that moment. This means the invoice retains the values as they existed when it was created, even if the party is edited later. These fields are writable in the POST body but default to the counterparty's live values if not supplied.

**Branch assignment.** `branch` is a slug field (not an ID). For branch-level roles (BRANCH_ADMIN, USER, KPO) it is always forced server-side to the user's own branch and cannot be overridden.

**Status.** Every transaction has a `status` field with two choices: `pending` or `paid`. This drives two behaviors — whether the counterparty's `balance_amount` is updated, and whether a second settlement journal entry is generated. A pending sales invoice adds to the party's balance (a receivable). A paid one does not.

**Auto-generated codes.** `sale_code`, `purchase_code`, `purchase_return_code`, `damage_return_code`, `damage_receiving_code` are all read-only. They are set by the server on creation and cannot be supplied or overridden by the client.

**Journal entries.** Every create or update triggers journal entry generation inside a database transaction. On update, the existing journal entries for that transaction are deleted and recreated from the new values. There is no separate journal endpoint — journals are an internal side effect only.

---

## Purchase Invoices

### GET /api/purchase-invoices/

Returns all purchase invoices visible to the requesting user.

### POST /api/purchase-invoices/

Creates a purchase invoice and increases stock for each line item.

Request body:
```json
{
  "date": "2025-01-15",
  "supplier": "uuid-of-supplier",
  "company": "uuid-of-company",
  "account": "uuid-of-account",
  "status": "pending",
  "s_tax": "1500.00",
  "freight": "200.00",
  "adv_income_tax": "0.00",
  "net_amount": "10700.00",
  "remarks": "January stock",
  "line_items": [
    {
      "item": "uuid-of-item",
      "carton": 10,
      "pcs": 120,
      "rate": "75.00",
      "amount": "9000.00",
      "discount_amount": "0.00",
      "to_rate": "0.00",
      "to_amount": "0.00",
      "s_tax_rate": "17.00",
      "s_tax_amount": "1530.00",
      "net_amount": "10530.00"
    }
  ]
}
```

The `supplier` must have `is_supplier=True`. Each line item's `pcs` value is added to `item.current_stock`. If `status` is `pending`, the `net_amount` is added to `supplier.balance_amount`.

### PATCH /api/purchase-invoices/{id}/

Partial update. Stock quantities are recalculated based on the difference between old and new line items.

### DELETE /api/purchase-invoices/{id}/

Reverses all stock changes and journal entries and deletes the record.

---

## Sales Invoices

### GET /api/sales-invoices/

### POST /api/sales-invoices/

Creates a sales invoice and reduces stock for each line item.

Request body:
```json
{
  "date": "2025-01-16",
  "party": "uuid-of-party",
  "company": "uuid-of-company",
  "account": "uuid-of-account",
  "order_booker": "uuid-or-null",
  "salesman": "uuid-or-null",
  "status": "pending",
  "discount": "0.00",
  "net_amount": "7200.00",
  "line_items": [
    {
      "item": "uuid-of-item",
      "carton": 5,
      "pcs": 60,
      "rate": "120.00",
      "amount": "7200.00",
      "s_tax_amount": "0.00",
      "f_tax_amount": "0.00",
      "gross_amount": "7200.00",
      "to_rate": "0.00",
      "to_amount": "0.00",
      "net_amount": "7200.00"
    }
  ]
}
```

The `party` must have `is_party=True`. Each line item's `pcs` is deducted from `item.current_stock`. If `status` is `pending`, `net_amount` is added to `party.balance_amount` (a receivable).

### PATCH /api/sales-invoices/{id}/

### DELETE /api/sales-invoices/{id}/

---

## Purchase Returns

Purchase returns reverse a purchase — stock goes back down, and the supplier's balance decreases if the return is pending.

### GET /api/purchase-returns/

### POST /api/purchase-returns/

```json
{
  "date": "2025-01-20",
  "party_inv_no": "SUP-INV-1234",
  "supplier": "uuid-of-supplier",
  "company": "uuid-of-company",
  "account": "uuid-of-account",
  "status": "pending",
  "s_tax": "0.00",
  "freight": "0.00",
  "adv_income_tax": "0.00",
  "net_amount": "1500.00",
  "line_items": [
    {
      "item": "uuid-of-item",
      "carton": 2,
      "pcs": 24,
      "rate": "75.00",
      "amount": "1800.00",
      "discount_amount": "0.00",
      "to_rate": "0.00",
      "to_amount": "0.00",
      "s_tax_rate": "0.00",
      "s_tax_amount": "0.00",
      "net_amount": "1800.00"
    }
  ]
}
```

`party_inv_no` is an optional reference to the supplier's original invoice number. Each line item's `pcs` is deducted from `item.current_stock`. If `status` is `pending`, `net_amount` is deducted from `supplier.balance_amount`.

### PATCH /api/purchase-returns/{id}/

### DELETE /api/purchase-returns/{id}/

---

## Damage Returns

Damage returns send damaged goods back to the supplier. They operate on `item.damaged_stock`, not `current_stock`.

### GET /api/damage-returns/

### POST /api/damage-returns/

```json
{
  "date": "2025-01-21",
  "supplier": "uuid-of-supplier",
  "company": "uuid-of-company",
  "account": "uuid-of-account",
  "status": "pending",
  "s_tax": "0.00",
  "net_amount": "900.00",
  "line_items": [
    {
      "item": "uuid-of-item",
      "carton": 1,
      "pcs": 12,
      "rate": "75.00",
      "amount": "900.00",
      "s_tax_rate": "0.00",
      "s_tax_amount": "0.00",
      "net_amount": "900.00"
    }
  ]
}
```

Note that damage return line items are simpler than purchase return line items — there is no `discount_amount`, `to_rate`, or `to_amount`. Also the header has no `freight` or `adv_income_tax`. Each line item's `pcs` is deducted from `item.damaged_stock`. If `status` is `pending`, `net_amount` is deducted from `supplier.balance_amount`.

### PATCH /api/damage-returns/{id}/

### DELETE /api/damage-returns/{id}/

---

## Damage Receivings

Damage receivings record when a customer returns damaged goods. They increase `item.damaged_stock` and reduce the customer's outstanding receivable.

### GET /api/damage-receivings/

### POST /api/damage-receivings/

```json
{
  "date": "2025-01-22",
  "party": "uuid-of-party",
  "salesman": "uuid-or-null",
  "company": "uuid-of-company",
  "account": "uuid-of-account",
  "status": "pending",
  "s_tax": "0.00",
  "net_amount": "600.00",
  "line_items": [
    {
      "item": "uuid-of-item",
      "manual_code": "DMG-001",
      "issue_units": 12,
      "pcs": 12,
      "rate": "50.00",
      "amount": "600.00",
      "s_tax_rate": "0.00",
      "s_tax_amount": "0.00",
      "gross_amount": "600.00",
      "net_amount": "600.00"
    }
  ]
}
```

The `party` must have `is_party=True` (a customer). `manual_code` and `issue_units` are unique to this transaction type — `manual_code` is a free-text reference, `issue_units` is the quantity noted on the damage report. Each line item's `pcs` is added to `item.damaged_stock`. If `status` is `pending`, `net_amount` is deducted from `party.balance_amount`.

### PATCH /api/damage-receivings/{id}/

### DELETE /api/damage-receivings/{id}/

---

## Journal Entries

There is no API endpoint for journal entries. They are created, updated, and deleted automatically as a side effect of every transaction save and delete. Each transaction gets one base journal entry (debit + credit pair) and, if `status=paid`, a second settlement entry. On any update the prior journal entries are discarded and regenerated. The double-entry accounting logic is covered in full in `backend/docs/06_accounting.md`.
