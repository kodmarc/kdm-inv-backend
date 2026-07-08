# API — Master Data

Master data covers the people and accounts that transactions reference: parties (customers/suppliers), account openings, order-bookers, and salesmen. All four follow the same pattern — standard CRUD, branch-scoped, with branch-level roles automatically assigned to their own branch on create.

All endpoints require authentication.

---

## Parties

A party is a counterpart in a transaction. The same model handles both customers and suppliers via two boolean flags — `is_party` marks customers, `is_supplier` marks suppliers. A single record can be both.

### GET /api/parties/

Returns all parties visible to the requesting user, scoped by organization and branch.

### POST /api/parties/

Creates a new party.

Request body:
```json
{
  "name": "Ahmad Brothers",
  "contact_no": "0300-1234567",
  "email": "ahmad@example.com",
  "is_party": true,
  "is_supplier": false,
  "ntn": "1234567-8",
  "gst_no": "12-23-9999-001-26",
  "credit_limit": "500000.00"
}
```

At least one of `is_party` or `is_supplier` must be true. `ntn`, `gst_no`, `credit_limit`, `email`, and `contact_no` are optional.

`balance_amount` is read-only and starts at zero. It is adjusted automatically as invoices and returns are created or updated — it should never be set directly.

When an invoice is created with `status: pending`, the counterparty's `balance_amount` increases (for a sales invoice or damage return) or decreases (for a damage receiving or purchase-side returns). When the invoice is paid, the balance is not affected.

`ntn` and `gst_no` are snapshot-copied onto each invoice at creation time so the invoice retains the values as they existed when the transaction occurred.

### PATCH /api/parties/{id}/

Partial update. `balance_amount` remains read-only.

### DELETE /api/parties/{id}/

Will fail if the party is referenced by any existing transaction.

---

## Account Openings

Account openings represent internal ledger accounts — cash accounts, bank accounts, or any account used to track movement of money. Every transaction is linked to one account, and that account's running balance is maintained automatically.

### GET /api/accounts/

Returns all accounts visible to the requesting user.

### POST /api/accounts/

Creates a new account.

Request body:
```json
{
  "name": "HBL Main Account",
  "code": "HBL-01",
  "opening_balance": "50000.00"
}
```

`code` is optional — if not provided it is auto-generated as ACC-0001, ACC-0002, etc., scoped to the branch. Both `name` and `code` are unique per branch.

`balance` is read-only. It is set to `opening_balance` when the account is created and then adjusted by every transaction that references this account. It cannot be patched directly.

### PATCH /api/accounts/{id}/

Partial update. `balance` remains read-only.

### DELETE /api/accounts/{id}/

Will fail if referenced by any transaction.

---

## Order Bookers

Order bookers are staff who take orders in the field. They can be optionally linked to sales invoices for reporting.

### GET /api/order-bookers/

Returns all order bookers visible to the requesting user.

### POST /api/order-bookers/

Request body:
```json
{
  "name": "Rizwan Ahmed",
  "contact_no": "0312-9876543",
  "email": "rizwan@example.com"
}
```

`contact_no` and `email` are optional. `branch` is auto-set for branch-level roles and cannot be overridden. `name` must be unique within the branch.

### PATCH /api/order-bookers/{id}/

### DELETE /api/order-bookers/{id}/

---

## Salesmen

Salesmen are linked to sales invoices and damage receivings for tracking purposes. The model is identical to order-booker in structure.

### GET /api/salesmen/

### POST /api/salesmen/

Request body:
```json
{
  "name": "Kamran Ali",
  "contact_no": "0333-1112223",
  "email": "kamran@example.com"
}
```

Same rules as order-bookers — name unique per branch, branch auto-set for branch roles.

### PATCH /api/salesmen/{id}/

### DELETE /api/salesmen/{id}/
