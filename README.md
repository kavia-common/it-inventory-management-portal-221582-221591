# it-inventory-management-portal-221582-221591

Backend: `inventario_backend/` (Django 5 + DRF)  
Database: `inventario_db/` (PostgreSQL)  
Frontend: `inventario_frontend/` (React)

This document focuses on how the Django backend owns and manages the PostgreSQL schema via migrations.

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

This migration is the single source of truth (together with the default Django auth/admin migrations) for the PostgreSQL schema.  
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

## Changing the schema safely

When you need to evolve the inventory data model (for example adding a field to `InventoryItem`):

1. Edit `inventario_backend/api/models.py`.
2. Generate migrations:

   ```bash
   cd inventario_backend
   python manage.py makemigrations api
   ```

3. Inspect the generated migration(s) under `inventario_backend/api/migrations/` to ensure the operations match your intent.
4. Apply the migrations:

   ```bash
   python manage.py migrate
   ```

5. Commit both the model changes and the migration files.

Following this workflow guarantees that the PostgreSQL schema in `inventario_db` remains consistent across all environments and fully controlled by Django.