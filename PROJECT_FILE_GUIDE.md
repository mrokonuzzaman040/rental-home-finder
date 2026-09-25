# HouseFinderBD — Project File Guide (Detailed)

This document explains the purpose, features, and internals of the repository. It helps developers and contributors find where to change behaviour, add features, and perform common development tasks.

Quick overview
- Project type: Django web application for listing and searching rental homes.
- Main app: `listings` — contains models, forms, views, templates, and business logic.
- Config: `config` Django project settings and URL routing.

Prerequisites & quick start
- Recommended: create and activate a virtual environment (`python -m venv venv && source venv/bin/activate`).
- Install dependencies: `pip install -r requirements.txt`.
- Apply migrations: `python manage.py migrate`.
- Create superuser: `python manage.py createsuperuser`.
- Run dev server: `python manage.py runserver`.
- Load demo data (if desired): `python seed.py` (inspects `seed.py` for dataset creation).

Project layout and responsibilities

- `manage.py` — Django management entry point. Use it to run the development server, migrations, tests, and other management commands.

- `config/`
	- `settings.py` — central configuration: INSTALLED_APPS, database settings, static/media settings, authentication backends, third-party service keys (if any), email and security settings, and other environment-specific overrides. For production, override sensitive values with environment variables or a secrets manager.
	- `urls.py` — root URL router. Registers `admin/` and includes the `listings` app's URLs.
	- `wsgi.py`, `asgi.py` — WSGI/ASGI entry points for deployments.

- `listings/` — core application providing the marketplace functionality. Key files:
	- `models.py` — ORM models for the domain: listings, inquiries, favorites, reviews, rewards, offers and related entities. Models persist listing metadata (address, price, features), owner relations, and counters (views, favorites).
	- `forms.py` — Django forms used for user-facing add/edit listing forms, registration, and other form-backed interactions. Includes validation (image size/type checks, field constraints).
	- `views.py` — page and API views: home, search, listing detail, compare, dashboard, add/edit/delete listing, favorites, profile, rewards pages, and JSON endpoints consumed by frontend widgets. Views implement pagination, permission checks, and form handling.
	- `admin.py` — admin customizations: admin model registration, list displays, filters, custom admin views and dashboard metrics used by staff.
	- `queryset.py` — shared QuerySet helpers and manager methods used by views and background tasks to filter, sort, and annotate listing queries (search, tenant filters, availability filters).
	- `choices.py` — canonical lookup values used across the app: city list, city coordinates for map modal, tenant type choices, feature flags. Update this file to add new cities or city metadata.
	- `geo.py` — geolocation helpers: distance calculations, lat/lon normalization, and integrations with any geocoding services.
	- `ai_utils.py` — utilities for AI-driven features such as the chat assistant, suggestion generation, or scheduled prompts. Contains integration points and wrappers to keep third-party keys isolated.
	- `validators.py` — custom field validators used by forms and models (e.g., image validation, phone number/ID checks).
	- `rewards.py` — business logic for the rewards/points system used in the site (granting points, redeeming offers).
	- `urls.py` — app-level URL patterns for all listing-related routes and AJAX/API endpoints.
	- `apps.py` — Django app configuration.
	- `tests.py` — unit and integration tests for models, forms, views and any custom logic.

- `templates/` — HTML templates used by the frontend.
	- `base.html` — main site layout (nav, footer, common includes). Use this to change global site HTML or include global JS/CSS.
	- `auth/` — pages for authentication and user dashboard: login, register, dashboard, add/edit listing, favorites, profile, messages, delete confirmation, rewards.
	- `listings/` — public listing templates: listings grid, listing detail page (`listing.html`), compare view, search page, and listing item partials.
	- `partials/` — small reusable fragments: `location_modal.html`, `location_modal_scripts.html`, `ai_chat_widget.html`. These are included by other templates and provide client JS hooks (search modal, AI chat widget integration).

- `static/` — static assets (CSS, JS, images). The admin CSS overrides and the site logo files live under `static/`.

- Top-level files
	- `requirements.txt` — pinned Python package dependencies. Update this when adding new packages.
	- `README.md` — high-level project README and setup instructions.
	- `seed.py` — script to seed the local DB with demo/test data. Inspect before running for any destructive actions.
	- `db.sqlite3` — local development SQLite DB (not for prod). Keep it out of production workflows and consider removing from source control if desired.

Feature map (what the app implements)
- Listing management: users can create, edit, and delete listing posts (title, description, price, city, features, images).
- Search & filtering: full listing browse with filters for city, tenant type, price range, facilities (garage/heating/etc.), and text search. Sorting and pagination supported.
- Listing detail: shows images, owner contact, map/location modal, related listings, view counters, and report/ask features.
- Compare view: select multiple listings to compare features side-by-side.
- User dashboard: manage your listings, view messages/inquiries, check favorites, and see rewards balance.
- Favorites & reviews: logged-in users can favorite listings and leave reviews; these are surfaced on listing pages and in dashboards.
- Inquiries & messages: basic inquiry form to contact listing owners; stored in DB and accessible in dashboard/messages.
- Rewards & offers: a points system where users earn points and redeem offers (see `rewards.py` and migrations for point-related schema).
- Admin dashboard: staff-facing metrics, listing moderation, and quick actions via `listings/admin.py` and custom admin templates.
- Geo helpers: location modal and city coordinates for map centering and proximity search.
- AI assistant: front-end chat widget and back-end utilities (`ai_utils.py`) used for assistance and automated tasks (daily prompts, suggested content); keys and external integrations are kept out of VCS.

Migrations summary
- The repository contains migration files in `listings/migrations/` that document the schema evolution. Notable migration names include:
	- `0002_listing_garage_listing_has_ac_listing_has_heating_and_more.py` — adds boolean fields for garage, AC, heating, etc.
	- `0003_listing_status_inquiry.py` — status/inquiry-related schema changes.
	- `0005_review_favorite.py` — review and favorite tables/relations.
	- `0006_listing_is_verified_listing_views_count.py` — verification flag and view counters.
	- `0007_rewards_points_offers.py` — rewards and offers schema.
	- `0008_ai_assistant_daily.py` — schema for AI assistant scheduling or logs.
	- `0009_listing_tenant_type.py` — tenant type enum/choices added.
	- `0010_city_choices_and_girl_tenant.py` — city choices and possible tenant-related adjustments.

Common development tasks and commands
- Install deps: `pip install -r requirements.txt`.
- Start dev server: `python manage.py runserver`.
- Apply DB migrations: `python manage.py migrate`.
- Create admin user: `python manage.py createsuperuser`.
- Run tests: `python manage.py test`.
- Linting / formatting: run your preferred linters/formatters (e.g. `flake8`, `black`) if configured locally.

Environment & configuration tips
- Keep production secrets (DATABASE_URL, SECRET_KEY, third-party API keys) out of `settings.py`. Use environment variables or a `.env` loader.
- For static files in production, collect them with `python manage.py collectstatic` and serve with a CDN or webserver.
- If switching the DB to PostgreSQL for production, update `config/settings.py` and install the appropriate DB adapter (`psycopg2-binary`).

Extending the project — where to change common behaviour
- Add a new city or update coordinates: edit `listings/choices.py`.
- Add a new filter (e.g., Elevator): add field to `models.py` (Listing), create migration, add form field in `forms.py`, expose filter in `queryset.py` and update front-end templates.
- Modify AI assistant behaviour: edit `listings/ai_utils.py` and any scheduled tasks or cron jobs that call it. Keep API keys in env variables.
- Change reward rules: update `listings/rewards.py` and create admin UI if needed in `admin.py`.
- Add API endpoints: add new view functions or Django REST Framework viewsets in `views.py` and expose them in `listings/urls.py`.

Troubleshooting notes
- The SQLite file `db.sqlite3` can lock if multiple processes access it. Use Postgres locally if you need concurrent processes.
- If templates don't update: ensure `DEBUG = True` during development or clear template caches.
- Static files 404 in production: run `collectstatic` and verify your static files settings and webserver configuration.

Where to look next
- Application entry: [manage.py](manage.py)
- Core app code: [listings/models.py](listings/models.py), [listings/views.py](listings/views.py), and [listings/forms.py](listings/forms.py)
- Config and deployment: [config/settings.py](config/settings.py)

If you'd like, I can:
- Add a one-page architecture diagram or Mermaid diagram summarizing components.
- Translate this guide back to Bengali (Bangla).
- Open and summarize any specific file or implement a small change (e.g., add a new city entry).

---
Last updated: 2026-05-15

