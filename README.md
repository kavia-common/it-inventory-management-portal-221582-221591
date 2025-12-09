# it-inventory-management-portal-221582-221591

Backend: `inventario_backend/` (Django 5 + DRF)  
Database: `inventario_db/` (PostgreSQL)  
Frontend: `inventario_frontend/` (React)

This document focuses on how the Django backend owns and manages the PostgreSQL schema via migrations, and how to seed minimal data for end-to-end validation.

---

## Database configuration (PostgreSQL)

The backend reads all connection details from environment variables; no manual SQL or schema management is required.

The `inventario_db` container exposes a connection string like:

```text
psql postgresql://appuser:dbuser123@localhost:5000/myapp
```

Django is configured in `inventario_backend/config/settings.py` to use the following environment variables:

- `POSTGRES_DB` (preferred) or `DB_NAME` — database name
- `POSTGRES_USER` (preferred) or `DB_USER` — database user
- `POSTGRES_PASSWORD` (preferred) or `DB_PASSWORD` — database password
- `POSTGRES_HOST` (preferred) or `DB_HOST` — database host
- `POSTGRES_PORT` (preferred) or `DB_PORT` — database port

If these variables are not set, the backend defaults are aligned with the `inventario_db` container:

- `DB_NAME=myapp`
- `DB_USER=appuser`
- `DB_PASSWORD=dbuser123`
- `DB_HOST=localhost`
- `DB_PORT=5000`

> IMPORTANT: Do **not** create or alter tables, indexes or constraints manually in PostgreSQL.  
> All schema changes must go through Django models + migrations.

You should define the variables above in a `.env` file (managed outside of this repo).  
Example (do **not** commit this file):

```env
# Django
SECRET_KEY=changeme-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL (backend <-> inventario_db)
POSTGRES_DB=myapp
POSTGRES_USER=appuser
POSTGRES_PASSWORD=dbuser123
POSTGRES_HOST=localhost
POSTGRES_PORT=5000

# CORS (frontend origin)
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

---

## Owning the schema with Django migrations

The `api` app defines all inventory models (locations, categories, items, movements, procedures, alerts) in:

- `inventario_backend/api/models.py`

The initial schema for these models is captured in:

- `inventario_backend/api/migrations/0001_initial.py`
- `inventario_backend/api/migrations/0002_userprofile.py`

These migrations are the single source of truth (together with the default Django auth/admin migrations) for the PostgreSQL schema.  
To keep the database in sync:

1. **Never** change the database schema manually with SQL.
2. When you modify or add models in `api/models.py`, always run:

   ```bash
   cd inventario_backend
   python manage.py makemigrations
   python manage.py migrate
   ```

3. Commit both:
   - the updated models, and
   - the new/updated `api/migrations/00xx_*.py` files.

Django’s migration history table (`django_migrations`) in PostgreSQL keeps track of which migrations have been applied, so the application can be safely deployed to fresh or existing databases.

---

## Running migrations (local / CI)

From the project root:

```bash
cd inventario_backend
```

Ensure the environment variables from the previous section are available (for example by loading your `.env`).

Then run:

```bash
# Apply all Django and app migrations (auth, admin, api, etc.)
python manage.py migrate
```

Optionally, create an admin user for accessing Django admin:

```bash
python manage.py createsuperuser
```

> Note: The `migrate` command will connect to the PostgreSQL instance exposed by `inventario_db`  
> using the configured `POSTGRES_*` / `DB_*` environment variables. If the connection fails,
> double‑check that the `inventario_db` container is running and that host/port/user/password
> match the values used in `inventario_db/db_connection.txt`.

---

## Seeding minimal data for end-to-end tests

To quickly verify the E2E flow between frontend and backend, a management command is provided:

```bash
cd inventario_backend

# (1) Make sure migrations are applied
python manage.py migrate

# (2) Optionally configure initial admin credentials via env (recommended)
export INITIAL_ADMIN_USERNAME=admin
export INITIAL_ADMIN_EMAIL=admin@example.com
export INITIAL_ADMIN_PASSWORD=admin123   # development only; choose a safer value in real envs

# (3) Seed minimal data
python manage.py seed_initial_data
```

The command will:

- Ensure an admin user exists with:
  - `is_staff=True`, `is_superuser=True`
  - an associated `UserProfile` with role `admin`
- Ensure at least one `Location` exists (code: `ISLA-001`)
- Ensure at least one `Category` exists (name: `Portátiles`)
- Ensure a sample `InventoryItem` exists:
  - code: `IT-DEMO-001`
  - linked to the sample Location/Category
  - owned by the seeded admin user

You can then:

1. Start the backend (usually on port `3001`).
2. Start the frontend (usually on port `3000`).
3. Log into the React app with the seeded admin credentials.
4. Navigate to the inventory, locations, and alerts views to confirm that:
   - the health endpoint `/api/health/` responds with `{"message": "Server is up!"}`,
   - `/api/items/`, `/api/locations/`, `/api/categories/`, `/api/movements/`,
     `/api/procedures/`, `/api/alerts/`, and `/api/auth/*` endpoints are reachable,
   - the sample item `IT-DEMO-001` appears in the general inventory and related filters.

---

## Verifying database readiness

To confirm that PostgreSQL is reachable from the backend environment:

1. Check that you can connect using the same URL as in `inventario_db/db_connection.txt`, e.g.:

   ```bash
   # From a shell in the backend environment
   psql postgresql://appuser:dbuser123@localhost:5000/myapp -c "SELECT 1;"
   ```

2. Once this succeeds, run Django migrations:

   ```bash
   cd inventario_backend
   python manage.py migrate
   ```

If `migrate` completes without errors, the schema is fully owned by Django migrations and the backend is ready to serve requests.

---

## Frontend API base URL and CORS

The React frontend reads the backend base URL from an environment variable:

- `inventario_frontend/.env.example`:

  ```env
  REACT_APP_API_BASE=http://localhost:3001/api
  ```

The API client (`inventario_frontend/src/api/client.js`) uses:

```js
const baseURL = process.env.REACT_APP_API_BASE || "http://localhost:3001/api";
```

Ensure you create a local `.env` in the frontend folder (not committed) with the correct value for your environment.

On the backend side, CORS is configured in `config/settings.py`. By default:

- If `CORS_ALLOWED_ORIGINS` is set (comma-separated), those values are used.
- Otherwise, `http://localhost:3000` is allowed by default to support local React dev server.

This ensures the browser can call the Django API from the React application running at `http://localhost:3000`.
