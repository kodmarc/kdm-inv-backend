# Authentication

## Strategy

Authentication uses JWT tokens stored in HttpOnly cookies rather than Authorization headers. This means JavaScript on the frontend cannot read the tokens — they are sent automatically by the browser with every request. This eliminates the risk of token theft via XSS.

Two cookies are set at login:

`access_token` — short-lived (15 minutes). Sent on every API call and validated by `CookieJWTAuthentication`.

`refresh_token` — long-lived (7 days). Only sent to `/api/auth/refresh/`. Used to silently obtain a new access token when the current one expires.

Both cookies are set with `HttpOnly=True`, `SameSite=Lax`, and `Secure=True` in production. In development (`DEBUG=True`) the Secure flag is dropped so cookies work over plain HTTP.


## CookieJWTAuthentication

This is a custom DRF authentication class in `accounts/authentication.py`. It replaces SimpleJWT's default header-based authentication.

On every request it reads `access_token` from `request.COOKIES`, validates the JWT signature and expiry using SimpleJWT's `UntypedToken`, and resolves the user from the token's `user_id` claim.

After validating the JWT, it manually enforces CSRF. For all paths except `/api/auth/`, it instantiates Django's `CSRFCheck` and calls it against the request. This means the API has both JWT authentication AND CSRF protection, closing the CSRF vulnerability that header-based auth is usually exempt from.

If either the JWT or CSRF check fails, the class returns `None` (anonymous user) or raises `AuthenticationFailed`.


## Multi-Tenant Authentication Backend

`accounts/backends.py` contains `MultiTenantAuthBackend`. This replaces Django's default authentication backend for login validation.

The difference from the standard backend is that it scopes username uniqueness to the organization. The same username can exist in two different organizations without conflict. The backend requires `org_id` to be passed alongside username and password, then looks up the user within that specific organization.

Django's standard `ModelBackend` is kept as a fallback for the admin panel, which authenticates globally.


## Login Flows

There are two login endpoints, one for HQ roles and one for branch roles.

`POST /api/auth/login-org/` accepts `org_id`, `role`, `username`, and `password`. The role must be `ORG_ADMIN` or `ORG_USER`. On success it sets both JWT cookies and returns the user profile plus a CSRF token in the response body.

`POST /api/auth/login-branch/` accepts `org_id`, `branch_slug`, `role`, `username`, and `password`. The role must be `BRANCH_ADMIN`, `USER`, or `KPO`. On success it sets cookies and returns the user profile with branch details plus a CSRF token.

Both endpoints explicitly call `get_token(request)` to generate the CSRF token and set the `csrftoken` cookie before responding. The CSRF token is also returned in the response body so the frontend can inject it into Axios default headers immediately.


## Token Refresh

`POST /api/auth/refresh/` reads the `refresh_token` cookie, validates it, and issues a new `access_token` cookie. If `ROTATE_REFRESH_TOKENS` is True (which it is), a new refresh token is also issued and the old one is blacklisted. SimpleJWT's token blacklist app handles this.

The frontend's Axios interceptor calls this endpoint automatically when it receives a 401. If refresh also fails, it fires an `auth-session-expired` custom event which the AuthContext listens to and uses to clear the user state.


## Logout

`POST /api/auth/logout/` blacklists the current refresh token and deletes both JWT cookies from the response. The frontend's AuthContext also clears its local user state on receiving the response.


## Session Restore

`GET /api/auth/me/` is called when the app loads to restore the session without requiring a new login. If the `access_token` cookie is valid, it returns the current user's profile including their organization policies. If not, it returns 401 and the frontend treats the session as expired.

The returned profile includes `company_creation_policy` and `item_creation_policy` from the user's organization so the frontend can gate UI elements without a separate settings fetch.


## JWT Configuration

```
ACCESS_TOKEN_LIFETIME  = 15 minutes
REFRESH_TOKEN_LIFETIME = 7 days
ROTATE_REFRESH_TOKENS  = True
BLACKLIST_AFTER_ROTATION = True
ALGORITHM = HS256
SIGNING_KEY = JWT_SIGNING_KEY from .env  (separate from SECRET_KEY)
```
