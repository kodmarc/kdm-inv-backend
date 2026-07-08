# KDM Inventory — Backend Overview

KDM Inventory is a multi-tenant POS and inventory management system built for businesses that operate across multiple branches. Each organization can have many branches, each branch manages its own companies, and all transactional data (invoices, returns, stock) is scoped beneath that hierarchy.

The backend is a REST API built with Django 5.2 and Django REST Framework. It handles authentication, multi-tenancy enforcement, inventory tracking, and double-entry accounting automatically on every transaction.


## Tech Stack

- Python 3.12
- Django 5.2
- Django REST Framework
- SimpleJWT with token blacklisting
- PostgreSQL via Supabase (PgBouncer pooler in transaction mode)
- django-environ for environment configuration
- Gunicorn for production serving (Render)


## Django Apps

The project is split into five focused apps plus the core configuration module.

`accounts` handles the custom User model, authentication backends, JWT cookie auth, and all login/signup/logout views.

`organizations` owns the Organization and Branch models, the auto-sequence generation system (BranchSequence), and the permission classes that enforce data-scoping policies.

`companies` is a lightweight app for the Company model. Companies are scoped to a branch or organization depending on the active policy.

`items` covers item categories and the item catalog. Items track current stock and are scoped the same way as companies.

`registers` is the largest app. It owns parties (suppliers/customers), ledger accounts, order bookers, salesmen, all invoice types, all return types, damage receiving, and the journal entry system.

`core` holds settings, root URL configuration, and WSGI/ASGI entry points.


## Local Setup

Clone the repository and navigate to the backend directory.

```
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Create a `.env` file in the backend root. See the Environment Variables section below.

```
python manage.py migrate
python manage.py runserver 8001
```

The API will be available at `http://localhost:8001/api/`.


## Environment Variables

```
SECRET_KEY=<django-secret-key>
JWT_SIGNING_KEY=<separate-key-for-jwt-signing>
DEBUG=True
DATABASE_URL=postgresql://user:password@host:5432/dbname
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5174
CSRF_TRUSTED_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
```

`DATABASE_URL` accepts the standard dj-database-url format. For Supabase, use the pooler URL (port 5432, transaction mode). SSL is applied automatically when the host contains `supabase`, `render`, or `aiven`.

`JWT_SIGNING_KEY` should be different from `SECRET_KEY`. It is used exclusively to sign JWT tokens.

`DEBUG=True` disables SSL redirect and keeps cookies insecure so they work over plain HTTP in local development. Never deploy with `DEBUG=True`.


## Running Tests

```
python manage.py test
```

Tests use SQLite automatically — the DATABASE_URL is ignored when `test` is in sys.argv.
