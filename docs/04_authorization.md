# Authorization

## Role System

Every user has exactly one role. There are five roles in the system, split into two tiers: HQ roles and branch roles.

HQ roles (`ORG_ADMIN`, `ORG_USER`) have no branch assignment. They operate at the organization level and can see all data across all branches when querying through HQ endpoints.

Branch roles (`BRANCH_ADMIN`, `USER`, `KPO`) are always assigned to a specific branch. Their data access is scoped to that branch automatically in every view.

`ORG_ADMIN` — Full control. Can change organization settings and policies, manage branches, manage users, and write to all catalog and transaction data through HQ routes.

`ORG_USER` — Like ORG_ADMIN but cannot change governance settings (policies, org name). Read access to everything, write access to catalog and transactions through HQ routes.

`BRANCH_ADMIN` — Manages a single branch. Can create and edit companies, items, parties, accounts, and all transactions within their branch, provided the active policy allows it.

`USER` — A branch-level operator. Can create and edit transactions. Whether they can create catalog items (items, companies) depends on the policy in force.

`KPO` — A cashier role. Currently restricted to the KPO checkout route only. Catalog and transaction write access is not yet implemented for this role.


## Creation Policies

The organization has two independent policy settings: `company_creation_policy` and `item_creation_policy`. Each can be either `ORG_ADMIN` (centralized) or `BRANCH_ADMIN` (decentralized).

When a policy is `ORG_ADMIN`, only users with `ORG_ADMIN` or `ORG_USER` roles can create or modify those records. Branch users will receive a 403 if they attempt to write.

When a policy is `BRANCH_ADMIN`, only users with `BRANCH_ADMIN` or `USER` roles (who also have a branch assigned) can write to those records. HQ users are also blocked by this policy mode.

Both policies default to `ORG_ADMIN` on a new organization. An ORG_ADMIN can change them at any time through the settings endpoint.


## PolicyBasedCRUDPermission

This DRF permission class lives in `organizations/permissions.py` and is applied to the Company, Item, and ItemCategory viewsets.

Each viewset declares a `policy_type` attribute — either `'company'` or `'item'`. The permission class reads the corresponding policy from the user's organization and enforces it on all write operations (POST, PUT, PATCH, DELETE). GET requests always pass.

The logic is straightforward: if the policy is `ORG_ADMIN`, the user's role must be in `['ORG_ADMIN', 'ORG_USER']`. If the policy is `BRANCH_ADMIN`, the user's role must be in `['BRANCH_ADMIN', 'USER']` and they must have a branch assigned. Any mismatch returns 403.


## IsOrganizationHQUser

This simpler permission class is used on endpoints that are always HQ-only regardless of policy, such as branch management (`/api/org-admin/branches/`) and user management (`/api/users/`). It allows the request only if the user's role is `ORG_ADMIN` or `ORG_USER`.


## Data Scoping in Views

Beyond the explicit permission classes, all views scope their querysets to `request.user.organization`. This means a user from Organization A can never read or modify data belonging to Organization B, even if they somehow obtain a valid JWT for a user in Organization A with similar credentials.

Branch-role users additionally have their querysets filtered to `request.user.branch` on endpoints where branch-level data isolation applies. The `validate()` method on each serializer also injects `branch=request.user.branch` automatically when a branch-role user creates a record, preventing branch users from assigning data to a different branch.


## Django Admin

The admin panel at `/admin/` is protected by Django's standard session-based authentication via `ModelBackend`. It is intended for superuser access only and is independent of the JWT auth system.
