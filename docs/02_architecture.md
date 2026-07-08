# Architecture

## Multi-Tenancy Model

The data hierarchy is: Organization → Branch → Company → Transactional Data.

Every model in the system carries an `organization` foreign key and an optional `branch` foreign key. When `branch` is null, the record is owned at the HQ level (visible to all branches). When `branch` is set, the record belongs to that branch only.

Companies and items sit one level deeper — they belong to a branch (or the org) and all transactional records (invoices, returns, stock) hang beneath a specific company.

This means two branches within the same organization are fully isolated from each other's stock, invoices, parties, and accounts while still sharing the same database.


## App Dependencies

```
core
 └── accounts       (User, auth, JWT)
 └── organizations  (Organization, Branch, BranchSequence, permissions)
      └── companies (Company)
           └── items (ItemCategory, Item)
                └── registers (Party, AccountOpening, Invoices, Returns, Journals)
```

Each app imports from the apps above it in this chain. `registers` is the leaf — it imports from all other apps but nothing imports from it.


## Middleware Chain

Django processes every request through this middleware stack in order:

1. SecurityMiddleware — enforces HTTPS in production, sets security headers
2. CorsMiddleware — handles cross-origin headers (must be high in the stack)
3. SessionMiddleware — enables session handling
4. CommonMiddleware — URL normalization
5. CsrfViewMiddleware — validates the CSRF token on all mutating requests
6. AuthenticationMiddleware — standard Django session auth (used for admin only)
7. MessageMiddleware — flash messages for Django admin
8. XFrameOptionsMiddleware — sets X-Frame-Options: DENY

API authentication does not use sessions. It is handled separately in DRF via `CookieJWTAuthentication` which runs per-request before the view executes.


## Request Lifecycle

When the frontend sends any API request, this is the path it takes:

The CORS middleware checks the Origin header against `CORS_ALLOWED_ORIGINS`. If it does not match, the response is rejected before anything else runs.

`CookieJWTAuthentication` reads the `access_token` cookie, validates the JWT signature and expiry, and sets `request.user` to the corresponding User instance. If the token is missing or invalid, `request.user` becomes `AnonymousUser`.

For all mutating requests (POST, PUT, PATCH, DELETE), `CsrfViewMiddleware` validates that the `X-CSRFToken` header matches the `csrftoken` cookie. The custom auth class also enforces this explicitly for `/api/` routes, skipping it only for `/api/auth/` endpoints (login, signup) where the user cannot yet have a CSRF token.

DRF's permission classes then run. The default is `IsAuthenticated`. Additional permissions like `PolicyBasedCRUDPermission` or `IsOrganizationHQUser` are declared per-view.

Finally the view itself runs, queries the database scoped to `request.user.organization`, and returns a JSON response.


## URL Structure

All API routes are prefixed with `/api/`. The root URL config includes each app's urls.py:

```
/api/auth/           →  accounts.urls
/api/org-admin/      →  organizations.urls
/api/companies/      →  companies.urls
/api/items/          →  items.urls
/api/item-categories/→  items.urls
/api/parties/        →  registers.urls
/api/accounts/       →  registers.urls
/api/order-bookers/  →  registers.urls
/api/salesmen/       →  registers.urls
/api/sales-invoices/ →  registers.urls
/api/purchase-invoices/ → registers.urls
/api/purchase-returns/  → registers.urls
/api/damage-returns/    → registers.urls
/api/damage-receiving/  → registers.urls
/api/journal-entries/   → registers.urls
```


## Security Headers

These headers are always set regardless of DEBUG mode:

- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`

In production (DEBUG=False), HTTPS is enforced via SSL redirect, HSTS is set to one year with subdomains and preload, and both session and CSRF cookies are marked Secure.
