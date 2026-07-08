# API — Organizations

These endpoints manage the organization's own settings, its branches, and its users. All require an authenticated HQ user (ORG_ADMIN or ORG_USER) unless noted otherwise.

---

## Organization Settings

### GET /api/org-admin/settings/

Returns the current organization's governance settings.

Response:
```json
{
  "name": "KDM Traders",
  "org_id": "kdm101",
  "company_creation_policy": "ORG_ADMIN",
  "item_creation_policy": "ORG_ADMIN"
}
```

Accessible to ORG_ADMIN and ORG_USER.

### PUT /api/org-admin/settings/

Updates the organization name and/or creation policies. Only ORG_ADMIN can call this endpoint.

Request body:
```json
{
  "name": "KDM Traders Ltd",
  "company_creation_policy": "BRANCH_ADMIN",
  "item_creation_policy": "BRANCH_ADMIN"
}
```

All fields are optional — only the fields provided are updated. Returns the full updated settings object on success.

Changing `company_creation_policy` to `BRANCH_ADMIN` immediately allows branch users to create companies. Changing it back to `ORG_ADMIN` immediately blocks them again. Branch users who are already logged in will see the policy update reflected the next time they call `/api/auth/me/` (which the frontend does on every branch page load via `refreshUser()`).

---

## Branches

### GET /api/org-admin/branches/

Returns all branches belonging to the authenticated user's organization.

### POST /api/org-admin/branches/

Creates a new branch. Only ORG_ADMIN and ORG_USER can create branches.

Request body:
```json
{
  "name": "Karachi Branch",
  "slug": "karachi"
}
```

`slug` must be URL-safe, lowercase, no spaces. It becomes part of branch-level URLs (e.g. `/branch/karachi/companies`). The slug is unique per organization.

### DELETE /api/org-admin/branches/{id}/

Deletes a branch. Protected — will fail if users, companies, or transactional data are linked to the branch.

---

## Users

### GET /api/users/

Returns all users in the authenticated user's organization. Accessible to ORG_ADMIN and ORG_USER.

### POST /api/users/

Creates a new user within the organization. Only ORG_ADMIN and ORG_USER can create users.

Request body:
```json
{
  "username": "branchadmin",
  "password": "securepassword",
  "role": "BRANCH_ADMIN",
  "branch": "karachi"
}
```

`branch` is the branch slug. Required for branch-role users (BRANCH_ADMIN, USER, KPO), must be null for HQ-role users (ORG_ADMIN, ORG_USER).

### PATCH /api/users/{id}/

Updates a user. Supports partial updates. Cannot change role to or from a role that conflicts with the branch assignment (e.g. assigning ORG_ADMIN to a branch).

### DELETE /api/users/{id}/

Deletes a user. Will fail if the user has linked transactional data.
