# Deployment

## Platform

The backend is deployed on Render using Gunicorn as the WSGI server. The start command is:

```
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
```

Render automatically provides the `PORT` environment variable. Static files are served via Django's `collectstatic` during the build phase.

---

## Environment Variables Checklist

These must be set in the Render dashboard (or equivalent) for production:

```
SECRET_KEY              Strong random string, at least 50 characters
JWT_SIGNING_KEY         Separate strong random string, used only for JWT signing
DEBUG                   False
DATABASE_URL            Full PostgreSQL connection string
ALLOWED_HOSTS           Your render domain, e.g. kdm-backend.onrender.com
CORS_ALLOWED_ORIGINS    Your frontend domain, e.g. https://kdm-frontend.vercel.app
CSRF_TRUSTED_ORIGINS    Same as CORS_ALLOWED_ORIGINS
```

Never set `DEBUG=True` in production. When DEBUG is False, the settings automatically enable SSL redirect, HSTS, and secure cookie flags.

---

## Database — Supabase + PgBouncer

The project uses Supabase-hosted PostgreSQL. The connection string uses the Supabase pooler URL:

```
postgresql://user:password@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
```

The `pooler.supabase.com` host routes through PgBouncer in transaction mode. A few things to be aware of:

SSL is required. The settings file detects `supabase` in the host string and applies `sslmode: require` automatically.

`SELECT FOR UPDATE` works in PgBouncer transaction mode because the lock is held for the duration of the enclosing transaction, and each Django `atomic()` block holds a single connection for its lifetime.

Prepared statements are not supported in transaction mode. Django does not use prepared statements by default so this is not an issue.

The direct connection URL (port 5432, no pooler) can be used for running migrations locally. The pooler URL should be used in production.

---

## Running Migrations in Production

Render can be configured to run `python manage.py migrate` as a pre-deploy command. Alternatively, run it manually via the Render shell:

```
python manage.py migrate
```

---

## Static Files

Run `python manage.py collectstatic --noinput` during the build. Render can be configured to serve static files directly, or you can point `STATIC_ROOT` to a CDN bucket.

---

## CORS and CSRF in Production

`CORS_ALLOWED_ORIGINS` must contain the exact frontend origin (protocol + domain, no trailing slash). Wildcards are not used.

`CSRF_TRUSTED_ORIGINS` must also contain the frontend origin. Django's CSRF middleware checks this for requests coming from the browser.

`CORS_ALLOW_CREDENTIALS = True` is required for cookies to be sent cross-origin.

In production the cookies will have `Secure=True` and `SameSite=Lax`. Ensure both frontend and backend are served over HTTPS.

---

## First-Time Setup

After deploying and running migrations, create a superuser for the Django admin:

```
python manage.py createsuperuser
```

The first organization is created via the signup endpoint (`POST /api/auth/signup/`) — no admin panel interaction needed for normal onboarding.
