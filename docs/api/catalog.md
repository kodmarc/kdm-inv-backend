# API — Catalog

The catalog covers companies, item categories, and items. These are the master lists that transactions reference. Who can write to them depends on the organization's creation policy — see `04_authorization.md` for the full policy explanation.

All endpoints require authentication. GET requests are allowed for all authenticated users regardless of policy.

---

## Companies

### GET /api/companies/

Returns all companies visible to the requesting user. HQ users see all companies in the organization. Branch users see only companies belonging to their branch (or HQ-level companies if the policy is centralized).

### POST /api/companies/

Creates a new company.

Request body:
```json
{
  "name": "KDM Consumer Products",
  "code": "KDM-CP"
}
```

`code` is optional. If omitted, one is auto-generated in the format COM-0001 scoped to the user's branch or org.

When `company_creation_policy` is `ORG_ADMIN`, only HQ users can call this endpoint. When it is `BRANCH_ADMIN`, only branch users can.

### PATCH /api/companies/{id}/

Partial update. Same policy enforcement applies.

### DELETE /api/companies/{id}/

Deletes the company if no items or transactions reference it.

---

## Item Categories

### GET /api/item-categories/

Returns all item categories visible to the requesting user.

### POST /api/item-categories/

Creates a new category.

Request body:
```json
{
  "name": "Beverages",
  "code": "BEV",
  "description": "Drinks and liquid products"
}
```

`code` and `description` are optional. Code auto-generates as CAT-0001 if not provided.

Policy enforcement mirrors the item policy — if `item_creation_policy` is `ORG_ADMIN`, only HQ users can create categories.

### PATCH /api/item-categories/{id}/

### DELETE /api/item-categories/{id}/

---

## Items

### GET /api/items/

Returns all items visible to the requesting user. Accepts an optional `?company_code=kdm-cp` query parameter to filter items by company. The branch company pages use this to load items specific to the active company.

### POST /api/items/

Creates a new item.

Request body:
```json
{
  "name": "Mineral Water 1.5L",
  "code": "MW-15",
  "category": "uuid-of-category",
  "company": "uuid-of-company",
  "pack": 12,
  "purchase_rate": "45.00",
  "sales_rate": "60.00",
  "sales_tax": "17.00",
  "is_active": true
}
```

All fields except `name` and `category` are optional. `pack` is the number of pieces per carton (used in invoice line item calculations). `current_stock` and `damaged_stock` are managed automatically and cannot be set directly through this endpoint.

Policy enforcement mirrors `item_creation_policy`.

### PATCH /api/items/{id}/

Partial update. `current_stock` and `damaged_stock` cannot be patched directly — they are updated only through invoice and return transactions.

### DELETE /api/items/{id}/

Soft-disabling via `is_active=false` is preferred over deletion to preserve transaction history.
