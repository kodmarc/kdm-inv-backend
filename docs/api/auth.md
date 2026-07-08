# API — Authentication

Base path: `/api/auth/`

All endpoints in this group are public (no authentication required) except `/api/auth/me/` and `/api/auth/logout/` which require a valid access token cookie.

---

## POST /api/auth/signup/

Creates a new organization and registers the first user as ORG_ADMIN.

Request body:
```json
{
  "org_id": "kdm101",
  "org_name": "KDM Traders",
  "username": "admin",
  "password": "securepassword"
}
```

`org_id` must be alphanumeric, at least 5 characters, contain at least one letter and one number. It is stored lowercase.

On success, sets `access_token` and `refresh_token` cookies and returns:
```json
{
  "user": {
    "id": "uuid",
    "username": "admin",
    "role": "ORG_ADMIN",
    "org_id": "kdm101",
    "org_name": "KDM Traders",
    "company_creation_policy": "ORG_ADMIN",
    "item_creation_policy": "ORG_ADMIN"
  },
  "csrf_token": "..."
}
```

Status 201 on success. 400 if org_id already exists or validation fails.

---

## POST /api/auth/login-org/

Authenticates an HQ-level user (ORG_ADMIN or ORG_USER).

Request body:
```json
{
  "org_id": "kdm101",
  "role": "ORG_ADMIN",
  "username": "admin",
  "password": "securepassword"
}
```

Sets cookies and returns the user profile plus `csrf_token`. The CSRF token must be stored by the frontend and injected into subsequent mutating requests as the `X-CSRFToken` header.

Status 200 on success. 400 for invalid credentials. 403 if the user's actual role does not match the requested role.

---

## POST /api/auth/login-branch/

Authenticates a branch-level user (BRANCH_ADMIN, USER, or KPO).

Request body:
```json
{
  "org_id": "kdm101",
  "branch_slug": "karachi",
  "role": "BRANCH_ADMIN",
  "username": "branchadmin",
  "password": "securepassword"
}
```

Returns the user profile with `branch_slug` and `branch_name` included.

Status 200 on success. 400 for invalid credentials or branch not found. 403 for role mismatch.

---

## POST /api/auth/logout/

Blacklists the current refresh token and clears both JWT cookies.

No request body required. Requires valid access token cookie.

Status 200 on success.

---

## POST /api/auth/refresh/

Exchanges the current `refresh_token` cookie for a new `access_token`. Also rotates the refresh token (issues a new one and blacklists the old one).

No request body required. The refresh token is read from the cookie automatically.

Status 200 on success. 401 if the refresh token is expired or blacklisted.

---

## GET /api/auth/me/

Returns the authenticated user's profile. Called on app load to restore the session.

No request body. Requires valid access token cookie.

Response:
```json
{
  "id": "uuid",
  "username": "admin",
  "role": "ORG_ADMIN",
  "org_id": "kdm101",
  "org_name": "KDM Traders",
  "branch_slug": null,
  "branch_name": null,
  "company_creation_policy": "ORG_ADMIN",
  "item_creation_policy": "ORG_ADMIN",
  "csrf_token": "..."
}
```

For branch users, `branch_slug` and `branch_name` are populated. `company_creation_policy` and `item_creation_policy` always reflect the current organization setting at the time of the call, not at login time.

Status 200 on success. 401 if no valid cookie.

---

## GET /api/auth/validate-org/

Validates that an org_id exists before showing the login form. Used by the login screen to give early feedback.

Query parameter: `?org_id=kdm101`

Returns a list of branches for the org (used to populate the branch dropdown on the branch login form).

Status 200 with branch list. 404 if org_id not found.
