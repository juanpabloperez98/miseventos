# Mis Eventos — Backend

REST API for **Mis Eventos**, an event management platform: users, events, sessions, speakers and
attendee registrations. Built with Flask on a hexagonal (ports and adapters) architecture.

> **Status.** Foundation (architecture, persistence, security, Docker, tests), authentication and
> **event management** (CRUD, status workflow, ownership, search and pagination), **session
> management**, **attendee registration**, a read-only **speaker catalog** and **event cover
> images** (Cloudinary) are implemented. Speaker management endpoints are not (see
> [Roadmap](#roadmap)).

## Tech stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.12 |
| Web framework | Flask 3 (application factory) |
| ORM / migrations | SQLAlchemy 2.1 / Alembic |
| Database | PostgreSQL 17 (driver: psycopg 3) |
| API docs & HTTP validation | flask-smorest (OpenAPI 3 + Swagger UI, marshmallow schemas) |
| Authentication | JWT (PyJWT, HS256) sent as `Authorization: Bearer <token>` |
| Password hashing | `hashlib.sha256()` with a per-user random salt |
| Dependency management | Poetry 2 |
| Tests | Pytest + pytest-cov |
| Quality | Ruff (lint + format), mypy (strict) |
| Runtime | Docker + Docker Compose; Flask dev server (development) or Gunicorn (production) |

## Architecture

Dependencies always point inward, towards the domain:

```text
      adapters/http (Flask)          infrastructure (SQLAlchemy, PyJWT, hashlib, config)
              │                                   │
              ▼                                   ▼
        application  (use cases, DTOs, authorization service)
              │
              ▼
           domain  (entities, value objects, enums, exceptions, ports)
```

- **Domain** — pure Python. Entities (`User`, `Event`, `EventImage`, `Session`, `Speaker`,
  `Registration`), value objects (`Email`, `TimeRange`, `PageRequest`/`Page`), enums, domain
  exceptions and the **ports** (abstract repositories, `UnitOfWork`, `PasswordHasher`,
  `TokenService`, `ImageStorage`). It imports no framework at all.
- **Application** — use cases orchestrate the domain through ports only. They never touch Flask,
  SQLAlchemy or PyJWT. Authorization (RBAC) lives here as `AuthorizationService`.
- **Infrastructure** — concrete adapters for the ports: SQLAlchemy models and repositories,
  `SqlAlchemyUnitOfWork`, `JwtTokenService`, `Sha256PasswordHasher`, settings, JSON logging.
- **Adapters (HTTP)** — Flask blueprints, marshmallow schemas, authentication/authorization
  decorators, error handlers. Routes only translate HTTP ⇄ use case calls.
- **Composition root** — `app/container.py` wires ports to implementations (one database
  session per request), and `app/bootstrap.py` exposes `create_app()`.

These rules are enforced by `tests/unit/test_architecture.py`, which fails if a layer imports a
forbidden module, if any module has a circular import, or if an adapter stops implementing its port.

### Folder structure

```text
back/
├── app/
│   ├── _telemetry/            # TELEMETRY_NAMESPACE (required by the technical test brief)
│   ├── domain/
│   │   ├── entities/          # User, Event, EventImage, Session, Speaker, Registration
│   │   ├── value_objects/     # Email, TimeRange, PageRequest, Page
│   │   ├── enums/             # UserRole, EventStatus, Permission
│   │   ├── exceptions/        # DomainError hierarchy
│   │   └── ports/             # repository / security / unit-of-work / image storage abstractions
│   ├── application/
│   │   ├── dto/               # commands, queries and output DTOs
│   │   ├── services/          # AuthorizationService (RBAC), EventAccessPolicy (ownership),
│   │   │                      # EventImagePolicy
│   │   └── use_cases/         # auth/, events/, event_images/, sessions/, registrations/,
│   │                          # speakers/, seeding/
│   ├── infrastructure/
│   │   ├── config/            # Settings loaded from environment variables
│   │   ├── database/          # base, session, models/, repositories/, unit_of_work
│   │   ├── images/            # CloudinaryImageStorage, DisabledImageStorage
│   │   ├── security/          # JwtTokenService, Sha256PasswordHasher
│   │   └── logging_config.py  # structured JSON logging
│   ├── adapters/cli/          # flask seed-initial-data command
│   ├── adapters/http/
│   │   ├── routes/            # health, auth, events, event_images, sessions, registrations,
│   │   │                      # speakers blueprints
│   │   ├── schemas/           # marshmallow request/response schemas
│   │   ├── middleware/        # authentication, authorization, request logging
│   │   ├── error_handlers.py  # domain exception -> HTTP status mapping
│   │   ├── openapi.py         # Swagger/OpenAPI + bearer security scheme
│   │   └── app_factory.py     # Flask wiring
│   ├── container.py           # dependency injection / composition root
│   └── bootstrap.py           # create_app()
├── migrations/                # Alembic environment and versions
├── tests/
│   ├── unit/                  # domain, application, infrastructure, architecture
│   └── integration/           # HTTP API and PostgreSQL repositories
├── Dockerfile               # image used by ../docker-compose.yml
├── alembic.ini
└── pyproject.toml / poetry.lock
```

### SOLID in practice

- **Single responsibility** — one use case per class (`RegisterUserUseCase`, `LoginUserUseCase`,
  …); routes only map HTTP; repositories only persist; error mapping lives in one module.
- **Open/closed** — new endpoints add a use case + route without editing existing ones; roles and
  permissions are a mapping injected into `AuthorizationService`; new domain errors inherit from a
  category (`NotFoundError`, `ConflictError`, …) and get the right HTTP status automatically.
- **Liskov substitution** — every adapter is interchangeable with its port; unit tests run the use
  cases against in-memory repositories instead of PostgreSQL.
- **Interface segregation** — one small port per aggregate plus separate `PasswordHasher`,
  `TokenService` and `UnitOfWork` ports, each exposing only the operations the endpoints need.
- **Dependency inversion** — use cases receive ports through their constructors; only
  `container.py` knows the concrete classes.

## Requirements

- Docker and Docker Compose v2 — enough to run everything.
- Optional, for running outside Docker: Python 3.12 and Poetry 2.

## Environment variables

Copy the templates and adjust the values. Application settings live in `back/.env`; the
infrastructure variables consumed by Docker Compose live in the repository root `.env`:

```bash
cp back/.env.example back/.env   # application settings
cp .env.example .env             # Docker Compose (repository root)
```

| Variable | Required | Description |
| --- | --- | --- |
| `FLASK_ENV` | no | `development` (default), `testing` or `production` |
| `DATABASE_URL` | yes | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@localhost:5432/miseventos` |
| `TEST_DATABASE_URL` | for integration tests | Must point to a database whose name ends in `_test` (created automatically) |
| `JWT_SECRET_KEY` | yes | At least 32 characters. In production it must also contain no placeholder (`replace-with`, `change-me`) and at least 16 distinct characters; generate it with `secrets.token_urlsafe(48)` |
| `JWT_EXPIRATION_MINUTES` | no | Access token lifetime, default `60` |
| `CORS_ORIGINS` | no | Comma-separated origins allowed on `/api/*` (e.g. the Angular dev server) |
| `LOG_LEVEL` | no | `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, `CRITICAL` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | yes (Docker) | PostgreSQL container credentials (root `.env`) |
| `POSTGRES_HOST_PORT` / `BACKEND_HOST_PORT` | no | Host ports published by Compose (root `.env`, defaults `5432` / `5000`) |
| `SEED_*` | no | Initial data seeder, see [Seed data](#seed-data). Any `SEED_*_ENABLED=true` with `FLASK_ENV=production` is a configuration error |
| `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | no | Event cover images, see [Event images](#event-images-cloudinary). All three or none; without them image uploads answer 503 |
| `CLOUDINARY_FOLDER` | no | Folder of the uploads, default `mis-eventos` (lowercase letters, digits, `-`, `_`) |
| `EVENT_IMAGE_MAX_BYTES` | no | Maximum image size, default `5242880` (5 MB) |
| `GUNICORN_WORKERS` / `GUNICORN_TIMEOUT` | no | Production only (`scripts/start.sh`): Gunicorn workers and worker timeout in seconds, defaults `2` / `30` |

The application refuses to start if a required variable is missing or invalid. Inside Docker
Compose, `DATABASE_URL` and `TEST_DATABASE_URL` are rebuilt from the `POSTGRES_*` variables so the
backend reaches PostgreSQL through the `postgres` service name, never `localhost`.

## Running with Docker (recommended)

Docker Compose belongs to the whole project, so run it from the repository root:

```bash
cp back/.env.example back/.env
cp .env.example .env
docker compose up --build
```

Compose starts PostgreSQL and waits for its health check. The backend container then runs
`scripts/start.sh`, in order and stopping at the first failure:

1. `alembic upgrade head` — apply migrations.
2. `flask --app app.bootstrap:create_app seed-initial-data` — create missing seed data (see
   [Seed data](#seed-data)).
3. `flask --app app.bootstrap:create_app run --debug` — the development server with hot reload
   (the source folder is mounted into the container).

If migrations or seeding fail, the container exits with a non-zero code instead of serving a
half-initialized API.

With `FLASK_ENV=production` (set by `../docker-compose.prod.yml`), step 2 is skipped (the seeder
refuses to run in production) and step 3 is replaced by Gunicorn
(`gunicorn 'app.bootstrap:create_app()'`, `GUNICORN_WORKERS` default 2). The production image is
built with `INSTALL_DEV=false`, so it has no dev dependencies. See the repository root `README.md`
for the full stack, including the Angular frontend.

All `docker compose` commands below are run from the repository root.

- API: <http://localhost:5000>
- Health: <http://localhost:5000/health>
- Swagger UI: <http://localhost:5000/docs>
- OpenAPI JSON: <http://localhost:5000/openapi.json>

Useful commands:

```bash
docker compose exec backend pytest tests/unit       # unit tests (no database)
docker compose exec backend pytest                  # unit + integration (uses TEST_DATABASE_URL)
docker compose exec backend pytest --cov=app        # with coverage
docker compose exec backend alembic upgrade head    # apply migrations
docker compose exec backend ruff check .            # lint
docker compose exec backend mypy                    # type check
docker compose down                                 # stop (keeps data)
docker compose down -v                              # stop and delete the postgres_data volume
```

## Running locally with Poetry

PostgreSQL must be reachable at the host/port in `DATABASE_URL` (for example `docker compose up -d
postgres`).

```bash
poetry install
poetry run alembic upgrade head
poetry run flask --app app.bootstrap:create_app seed-initial-data   # optional
poetry run flask --app app.bootstrap:create_app run --debug
```

## Seed data

`flask seed-initial-data` creates data for manual testing. Docker runs it on every start, after
the migrations and before the server. It only creates what is missing, so restarting the container
never duplicates data.

### What is created

| Data | Details |
| --- | --- |
| Users | One `ADMIN`, one `ORGANIZER` and one `ATTENDEE`, from the `SEED_*` variables |
| Speakers | 3 speakers (`app/application/use_cases/seeding/catalog.py`) |
| Events | 4 events owned by the seed organizer: 2 `PUBLISHED` (upcoming, with free seats), 1 `DRAFT` (upcoming), 1 `COMPLETED` (past) |
| Sessions | 7 sessions with speakers, inside their event's schedule |
| Registrations | None, so the registration flow can be tried by hand |

Event dates are relative to the day each event is first seeded. Statuses are reached through the
normal transitions (`DRAFT → PUBLISHED → COMPLETED`).

### Configuring the seed users

Set these variables in `back/.env` (`back/.env.example` has placeholder values):

| Variable | Description |
| --- | --- |
| `SEED_ADMIN_ENABLED` / `SEED_ORGANIZER_ENABLED` / `SEED_ATTENDEE_ENABLED` | `true` to create that user. Default `false` |
| `SEED_<ROLE>_NAME` / `SEED_<ROLE>_EMAIL` / `SEED_<ROLE>_PASSWORD` | Required when the user is enabled. Password: 8–128 characters |
| `SEED_DEMO_DATA_ENABLED` | `true` to create speakers, events and sessions. Requires `SEED_ORGANIZER_ENABLED=true`. Default `false` |

Replace the placeholder passwords before sharing an environment. Passwords are hashed with the
existing `PasswordHasher` (salted SHA-256) and never logged.

**Changing credentials.** The seeder never modifies an existing user. Changing a `SEED_*` value
only affects users created afterwards:

- To use a new email, change `SEED_<ROLE>_EMAIL` and restart. A new user is created; the old one
  is left untouched.
- To change the password of an existing seed user, update it in the database (there is no
  password-change endpoint yet). Alternatively, recreate the development database with
  `docker compose down -v`, which deletes all data.

**Existing emails.** If a seed email already belongs to a user, that user is kept as it is. Its
name, password and role are not changed, and it is never promoted. A role mismatch logs a
`seed_user_role_mismatch` warning. If the organizer email belongs to a non-organizer, demo data is
skipped with a `seed_demo_data_skipped` warning. Public registration always creates `ATTENDEE`
users.

### How idempotency works

- **Users** are matched by their normalized email (`strip().lower()`, the same rule as
  registration). The unique index on `users.email` is the final guard.
- **Speakers, events and sessions** each have a stable key, for example
  `event:bogota-python-summit`. The `seed_records` table maps each key to the id of the row created
  for it:
  - **Key recorded and row exists:** nothing happens. Manual edits (name, dates, status…) are kept.
  - **Key missing, or row deleted:** only that row is created, and the key points to the new id.
    Deleting a seed event or session by hand makes it come back on the next start. Deleting an event
    also deletes its sessions, so they are recreated with it.
  - **Session that no longer fits its event:** if a seed session is missing but no longer fits its
    manually edited event, it is skipped with a `seed_session_skipped` warning. Events are never
    moved.
- Relations use the real ids read from the database, never assumed ids.
- Everything runs in one transaction. On any error nothing is saved, and the command exits with a
  non-zero code and a clear message.

### Running it manually

```bash
docker compose exec backend flask --app app.bootstrap:create_app seed-initial-data
poetry run flask --app app.bootstrap:create_app seed-initial-data      # outside Docker
```

The output summarizes the result, for example
`Initial data ready: users created=0 existing=3; demo records created=0 existing=14 skipped=0`.

### Disabling it

Set the `SEED_*_ENABLED` variables to `false`, or remove them, since every seed is disabled by
default. With everything disabled, the command creates nothing and Docker starts normally. Seeding
never runs from `create_app()`, so tests, other CLI commands and the reloader never trigger it.

### Production protection

The command refuses to run when `FLASK_ENV=production`. It exits with a non-zero code and makes no
database changes. In addition, loading the settings with `FLASK_ENV=production` fails if any
`SEED_*_ENABLED` is true, so neither the API nor any `flask` command starts with seeding enabled in
production; `../docker-compose.prod.yml` forces all of them to `false`. Do not enable seed users with known passwords in any shared environment.

## Migrations

```bash
alembic upgrade head                                     # apply all migrations
alembic downgrade -1                                     # revert the last one
alembic revision --autogenerate -m "describe change"     # generate from model changes
alembic check                                            # fail if models and migrations diverge
```

Prefix with `poetry run` locally or `docker compose exec backend` in Docker. The database URL is
always taken from `DATABASE_URL`; `alembic.ini` contains no credentials.

## Tests and coverage

```bash
pytest tests/unit                      # unit tests only, no database needed
pytest tests/integration               # integration tests (most need TEST_DATABASE_URL)
pytest                                 # both
pytest --cov=app
pytest --cov=app --cov-report=html     # report in htmlcov/
```

Inside the development container `TEST_DATABASE_URL` is always set by `docker-compose.yml`
(`<POSTGRES_DB>_test`), so `pytest` there runs both suites and creates that database if it does not
exist. Without the variable, the tests that need the database are reported as skipped, and the
coverage then does not include them.

- `tests/unit` needs no database: domain rules, use cases with in-memory fakes, JWT, password
  hashing, settings and architecture rules.
- `tests/integration` covers the HTTP API and the SQLAlchemy repositories against real PostgreSQL.
  The session runs every Alembic migration on `TEST_DATABASE_URL` (upgrade at start, downgrade at
  the end) and each test runs inside a transaction that is rolled back. Tests that need the
  database are skipped when `TEST_DATABASE_URL` is not set.

## API

### Implemented

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/health` | — | Liveness check, returns `{"status": "ok"}` |
| POST | `/api/auth/register` | — | Self-registration (role `ATTENDEE`) |
| POST | `/api/auth/login` | — | Returns a JWT access token |
| GET | `/api/auth/me` | Bearer | Current user |
| GET | `/api/events` | optional | Paginated catalog: `?search=` (name), `?status=`, `?page=`, `?per_page=` (max 100) |
| POST | `/api/events` | Bearer (ADMIN, ORGANIZER) | Create a `DRAFT` event owned by the caller |
| GET | `/api/events/{id}` | optional | Event detail |
| PUT | `/api/events/{id}` | Bearer (ADMIN, owner) | Replace editable fields and optionally change `status` |
| DELETE | `/api/events/{id}` | Bearer (ADMIN, owner) | Delete a draft (204) or cancel a published event (200) |
| GET | `/api/events/{event_id}/sessions` | optional | Sessions of a visible event, ordered by start time |
| POST | `/api/events/{event_id}/sessions` | Bearer (ADMIN, event owner) | Create a session in the event |
| GET | `/api/sessions/{id}` | optional | Session detail |
| PUT | `/api/sessions/{id}` | Bearer (ADMIN, event owner) | Replace the session's editable fields |
| DELETE | `/api/sessions/{id}` | Bearer (ADMIN, event owner) | Delete the session (204) |
| POST | `/api/events/{event_id}/registrations` | Bearer | Register the authenticated user to the event (201) |
| GET | `/api/me/registrations` | Bearer | Events the authenticated user is registered to |
| POST | `/api/events/{event_id}/images/upload` | Bearer (ADMIN, event owner) | Signed parameters for a direct upload to Cloudinary (body: `filename`, `content_type`, `size`) |
| POST | `/api/events/{event_id}/images/confirm` | Bearer (ADMIN, event owner) | Verify the upload with Cloudinary and set it as the event cover (201) |
| DELETE | `/api/events/{event_id}/images` | Bearer (ADMIN, event owner) | Remove the event cover (204) |
| GET | `/api/speakers` | optional | Read-only speaker catalog ordered by name (`?page=`, `?per_page=` max 100); `id`, `name`, `bio` (no email) |

### Authentication rules

- `POST /api/auth/register` requires `name`, `email` and `password` (8–128 characters). The email
  is normalized (trimmed, lower-cased) and must be unique (409 `Email is already registered`).
  Public registration always creates an `ATTENDEE`; fields such as `role`, `id` or
  `password_hash` are rejected (422). Privileged roles are managed outside the public API.
- Passwords are hashed with `hashlib.sha256()` and a per-user random salt, never stored or
  returned in plain text, and never logged.
- `POST /api/auth/login` returns a JWT (`HS256`, `sub` and `role` claims, configurable expiry).
  Unknown emails and wrong passwords get the same 401 response, and unknown emails are verified
  against an unmatchable hash so both paths take a similar time.
- Protected routes answer 401 when the token is missing, malformed, forged, expired or belongs to
  a deleted user, and 403 when an authenticated user lacks the required permission. Permissions
  use the role stored in the database, not the role claim inside the token.

### Event management rules

- **Creation**: only roles with the `events:manage` permission (ADMIN, ORGANIZER). `created_by` is
  always the authenticated user and the status is always `DRAFT`. Payloads containing `id`,
  `created_by`, `status`, `created_at` or `updated_at` are rejected with 422 (no mass assignment).
- **Ownership**: ADMIN (`events:manage_any`) manages every event, ORGANIZER only the events they
  created, ATTENDEE none. Enforced in the use cases through `EventAccessPolicy`, never in routes.
- **Visibility**: anonymous users and attendees only see `PUBLISHED` events; organizers also see
  their own events; admins see everything. Hidden events answer 404 so their existence is not
  leaked. A supplied but invalid token always answers 401, even on public endpoints.
- **Status workflow**: `DRAFT → PUBLISHED | CANCELLED`, `PUBLISHED → CANCELLED | COMPLETED`.
  `CANCELLED` and `COMPLETED` are final: they cannot change status nor be edited (409).
- **Validation**: non-blank name (≤ 200) and location (≤ 255), description ≤ 5000, integer
  `capacity > 0` (≤ 1,000,000), timezone-aware dates with `start_date < end_date`. Dates are
  stored and returned in UTC (see [Dates and timezones](#dates-and-timezones)).
- **Capacity**: cannot be lowered below the number of registered attendees (409). The event row
  is locked (`SELECT … FOR UPDATE`) while it is updated.
- **Removal**: `DRAFT` is physically deleted (204); `PUBLISHED` is cancelled instead (200 with the
  cancelled event); `CANCELLED` and `COMPLETED` cannot be removed (409).
- **Search**: case-insensitive partial match on the event **name**, executed in PostgreSQL with
  bound parameters and `LIMIT/OFFSET` pagination.

Errors always use the same JSON shape:

```json
{ "message": "Request validation failed", "errors": { "json": { "email": ["Not a valid email address."] } } }
```

Domain errors map to statuses by category: invalid value → 422, not found → 404, conflict → 409,
authentication → 401, authorization → 403. Unexpected errors return
`{"message": "Internal server error"}` and are logged; stack traces are never returned.

### Session management rules

- A session always belongs to the event in the URL; `event_id` cannot be sent nor changed.
- **Ownership is derived from the event**: whoever can manage the event (ADMIN, or the ORGANIZER
  who created it) can manage its sessions, through the same `EventAccessPolicy`. ATTENDEE cannot.
- **Visibility follows the event**: sessions of events the caller cannot see answer 404.
- **Schedule**: `start_time < end_time` and the session must fit within the event
  (`event.start_date <= start_time` and `end_time <= event.end_date`, boundaries included).
- **Capacity**: required integer greater than zero (≤ 1,000,000). Attendee registration to
  sessions is not part of this phase.
- **Speaker**: optional; when `speaker_id` is sent the speaker must exist (404 otherwise).
  Omitting it on `PUT` removes the speaker.
- **Event status**: sessions of `CANCELLED` or `COMPLETED` events cannot be created, updated or
  deleted (409), the same rule that already prevents editing those events.

### Attendee registration rules

- The registered user is always the authenticated user; the request body must be empty and any
  field such as `user_id` is rejected (422). `GET /api/me/registrations` takes no user parameter.
- Events the user cannot see answer 404, exactly like `GET /api/events/{id}`. Visible events that
  are not `PUBLISHED` answer 409 (`Event is not open for registration`).
- A user registers at most once per event (409), enforced in the use case and by the database
  constraint `UNIQUE(user_id, event_id)`.
- Capacity is never exceeded (409 `Event has reached its capacity`): the use case locks the event
  row with `SELECT … FOR UPDATE`, then checks duplicates, counts registrations and inserts in the
  same transaction, so concurrent registrations to the same event are serialized. Each request
  uses its own database session and unit of work. `tests/integration/database/
  test_registration_concurrency.py` runs real concurrent transactions to verify it.
- The list keeps events that were cancelled or completed after the user registered.

### Event images (Cloudinary)

Each event can have **one cover image** (`event_images` table, `event_id` unique, deleted with the
event). Files go from the browser straight to Cloudinary: the backend only signs the upload and
verifies it, it never receives nor downloads the file.

1. **Authorize** — `POST /api/events/{id}/images/upload` with `filename`, `content_type` and `size`.
   The backend checks the user can manage the event (ADMIN or owner, not cancelled/completed),
   the type (`image/jpeg`, `image/png`, `image/webp`) and the size (`EVENT_IMAGE_MAX_BYTES`). It
   returns `upload_url`, `cloud_name`, `api_key`, `timestamp`, `signature`, `public_id` and
   `allowed_formats`. The `public_id` (`<folder>/events/<event_id>/<random>`) and the formats are
   chosen and signed by the server with the official SDK (`cloudinary.utils.api_sign_request`), so
   the client cannot change them; Cloudinary rejects signatures older than one hour.
2. **Upload** — the browser POSTs the file with those fields to `upload_url` (multipart).
3. **Confirm** — `POST /api/events/{id}/images/confirm` with the `public_id`. The backend checks
   permissions again and that the id was issued for this event, then reads the image metadata from
   the Cloudinary Admin API (never from the client): it must exist, be JPEG/PNG/WebP and not exceed
   the size limit (otherwise it is deleted from Cloudinary and the request answers 422). Only then
   are `public_id`, `secure_url`, `width`, `height`, `format` and `bytes` stored. Confirming the
   current image again returns it unchanged (no duplicates).

**Replacement, deletion and failures.** No database transaction stays open during a Cloudinary call:
the read transaction is closed before verifying the upload, and the event row is locked again only
to save. Cloudinary deletions always happen *after* the commit:

- Replacing: the new image is saved first; the previous file is deleted only once the new one is
  committed. If saving fails, the new upload is deleted (compensation) and the old cover is kept.
- `DELETE /api/events/{id}/images` and deleting a draft event: the row is removed (cascade for the
  event), then the file. Cancelling a published event keeps its image.
- If a Cloudinary deletion fails, the database change stands and the file is left orphaned; the
  warning `event_image_cleanup_failed` logs its `public_id` for a manual cleanup. Each `public_id`
  is unique and belongs to one event, so deleting it never affects another event.
- An upload that is never confirmed (e.g. the user leaves during the upload) also stays orphaned in
  the folder of its event. There is no background job; it can be cleaned from the Cloudinary console.

Cloudinary errors answer **502** and missing configuration **503**, with generic messages: secrets,
signatures and Cloudinary error details are never returned nor logged.

**Delivery.** The frontend builds the URLs (see `front/README.md`): `f_auto,q_auto,c_fill,g_auto`
plus the width/height of each use. Cloudinary generates each size on demand and caches it in its
CDN; only the original is stored.

**Setting up Cloudinary.** Create a (free) account at <https://cloudinary.com>, copy *Cloud name*,
*API key* and *API secret* from *Settings > API Keys* into `back/.env` and restart the backend
(`docker compose up -d backend`). Compose passes `back/.env` to the backend only; the frontend
needs no configuration. The production CSP of Nginx already allows `https://res.cloudinary.com`
(images) and `https://api.cloudinary.com` (uploads).

**Migration.** `20261009_f0dc0e29f28d_create_event_images_table` only creates `event_images`;
existing events are untouched and are returned with `"image": null`. Docker applies it on start
(`alembic upgrade head` in `scripts/start.sh`); manually: `docker compose exec backend alembic
upgrade head`.

**Tests.** They never call Cloudinary: use cases run with a fake storage, the adapter tests replace
the SDK calls, and the API tests inject the fake into the container
(`tests/unit/application/test_event_image_use_cases.py`,
`tests/unit/infrastructure/test_cloudinary_image_storage.py`,
`tests/integration/http/test_event_images_api.py`). Run them with `docker compose exec backend
pytest`.

### Dates and timezones

- Every date column is `timestamptz` (`DateTime(timezone=True)`): event and session schedules,
  `registered_at`, `created_at` and `updated_at` are instants. There are no naive timestamps nor
  date-only columns.
- The API only accepts dates with an offset (`2030-10-10T14:30:00-05:00`, `…Z`); naive values are
  rejected with 422. Input is normalized to UTC and every date is returned as ISO 8601 in UTC
  (`+00:00`), whatever the `TimeZone` of the PostgreSQL session (`UtcDateTime` in
  `adapters/http/schemas/common.py`).
- The server timezone is not changed: the Docker containers and PostgreSQL run in UTC, and the code
  never relies on it (`datetime.now(UTC)`, never a naive `datetime.now()`). Audit timestamps come from
  PostgreSQL `now()`, which is an instant as well.
- Presentation is the frontend's job: it shows instants in Colombia time (`America/Bogota`).

### Roadmap

`GET /api/speakers` (read-only, used to assign speakers to sessions) is available. Ports,
repositories and domain rules for managing speakers already exist; a later phase could add:

```text
POST /api/speakers, PUT/DELETE /api/speakers/{id}
```

## Key design decisions

- **Event search uses parameterized queries.** The test brief suggests building the search SQL by
  concatenating f-strings. That would allow SQL injection, so the name search uses SQLAlchemy
  `icontains(..., autoescape=True)`. User input is always a bound parameter, and `%` / `_` are
  escaped. Integration tests confirm that injection payloads are treated as literal text.
- **SHA-256 password hashing, salted.** The brief mandates `hashlib.sha256()`. Each password gets a
  random 16-byte salt (`salt$digest`), and verification uses a constant-time comparison. A
  dedicated KDF such as bcrypt or argon2 would be stronger. The `PasswordHasher` port makes that a
  one-class swap.
- **Registration concurrency.** `EventRepository.get_by_id_for_update` issues
  `SELECT … FOR UPDATE` on the event row. The registration use case runs in one transaction:
  lock the event → count registrations → `Event.ensure_can_accept_registration()` → insert →
  commit. Concurrent requests for the last seat are serialized by the row lock, and the
  `UNIQUE(user_id, event_id)` constraint is the final guard against duplicates (mapped to
  `AlreadyRegisteredToEventError`).
- **Business rules live in the domain**: capacity and published-status checks (`Event`),
  `start < end` (`TimeRange`), sessions inside the event schedule (`Session.ensure_fits_within`).
  The database repeats the critical invariants as CHECK/UNIQUE constraints.
- **Three validation levels, kept apart**: HTTP shape in marshmallow schemas, business rules in
  the domain, integrity in database constraints.
- **Authentication ≠ authorization.** `@authenticated` resolves the user from the bearer token,
  and `@require_permission(...)` checks the role against `AuthorizationService`. The role is read
  from the database on every request, so role changes take effect without reissuing tokens.
- **Plain SQLAlchemy instead of Flask-SQLAlchemy**, so persistence does not depend on Flask. The
  container opens one session per request and closes it on teardown. Use cases commit through the
  `UnitOfWork` port.
- **Enums stored as constrained strings** (`VARCHAR` + `CHECK`) instead of native PostgreSQL enum
  types. This keeps migrations simple.
- **Indexes**: unique `users.email`; `events.name`; `(events.status, events.start_date)` for the
  public listing; foreign-key indexes on `events.created_by`, `registrations.event_id`,
  `sessions.event_id`, `sessions.speaker_id`. Lookups by `registrations.user_id` use the leading
  column of the `UNIQUE(user_id, event_id)` index, so a separate index would be redundant. For large
  data sets, a `pg_trgm` GIN index would speed up `ILIKE '%term%'` searches.
- **Referential actions**: deleting an event cascades to its sessions and registrations. Deleting a
  user cascades to their registrations but is blocked if they created events. Deleting a speaker
  sets `sessions.speaker_id` to `NULL`.
- **Structured logging**: JSON lines on stdout. Every record carries the telemetry namespace
  `miseventos.events.v1`. Passwords, tokens and secrets are never logged.
- **One image, two modes**: by default the container runs migrations, idempotent seeding and the
  Flask development server with hot reload. `docker-compose.prod.yml` switches to
  `FLASK_ENV=production`: migrations and Gunicorn, no seeding, no dev dependencies, no source mount,
  and the port is published on `127.0.0.1` only (the API is reached through an Nginx on the host).
