# Mis Eventos — Backend

REST API for **Mis Eventos**, an event management platform: users, events, sessions, speakers and
attendee registrations. Built with Flask on a hexagonal (ports and adapters) architecture.

> **Status.** Foundation (architecture, persistence, security, Docker, tests), authentication and
> **event management** (CRUD, status workflow, ownership, search and pagination), **session
> management** and **attendee registration** are implemented. Speaker management is next (see
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
| Runtime | Docker + Docker Compose (local development) |

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

- **Domain** — pure Python. Entities (`User`, `Event`, `Session`, `Speaker`, `Registration`),
  value objects (`Email`, `TimeRange`, `PageRequest`/`Page`), enums, domain exceptions and the
  **ports** (abstract repositories, `UnitOfWork`, `PasswordHasher`, `TokenService`). It imports no
  framework at all.
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
│   ├── _telemetry/            # TELEMETRY_NAMESPACE (required by the test)
│   ├── domain/
│   │   ├── entities/          # User, Event, Session, Speaker, Registration
│   │   ├── value_objects/     # Email, TimeRange, PageRequest, Page
│   │   ├── enums/             # UserRole, EventStatus, Permission
│   │   ├── exceptions/        # DomainError hierarchy
│   │   └── ports/             # repository / security / unit-of-work abstractions
│   ├── application/
│   │   ├── dto/               # commands, queries and output DTOs
│   │   ├── services/          # AuthorizationService (RBAC), EventAccessPolicy (ownership)
│   │   └── use_cases/         # auth/, events/ (create, get, list, update, delete)
│   ├── infrastructure/
│   │   ├── config/            # Settings loaded from environment variables
│   │   ├── database/          # base, session, models/, repositories/, unit_of_work
│   │   ├── security/          # JwtTokenService, Sha256PasswordHasher
│   │   └── logging_config.py  # structured JSON logging
│   ├── adapters/http/
│   │   ├── routes/            # health, auth, events blueprints
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
| `FLASK_ENV` | no | `development` (default) or `testing` |
| `DATABASE_URL` | yes | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@localhost:5432/miseventos` |
| `TEST_DATABASE_URL` | for integration tests | Must point to a database whose name ends in `_test` (created automatically) |
| `JWT_SECRET_KEY` | yes | At least 32 characters |
| `JWT_EXPIRATION_MINUTES` | no | Access token lifetime, default `60` |
| `CORS_ORIGINS` | no | Comma-separated origins allowed on `/api/*` (e.g. the Angular dev server) |
| `LOG_LEVEL` | no | `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, `CRITICAL` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | yes (Docker) | PostgreSQL container credentials (root `.env`) |
| `POSTGRES_HOST_PORT` / `BACKEND_HOST_PORT` | no | Host ports published by Compose (root `.env`, defaults `5432` / `5000`) |

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

Compose starts PostgreSQL, waits for its health check, then starts the backend, which runs
`alembic upgrade head` and the Flask development server with hot reload (the source folder is
mounted into the container).

All `docker compose` commands below are run from the repository root.

- API: <http://localhost:5000>
- Health: <http://localhost:5000/health>
- Swagger UI: <http://localhost:5000/docs>
- OpenAPI JSON: <http://localhost:5000/openapi.json>

Useful commands:

```bash
docker compose exec backend pytest                  # run the test suite
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
poetry run flask --app app.bootstrap:create_app run --debug
```

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
pytest
pytest --cov=app
pytest --cov=app --cov-report=html     # report in htmlcov/
```

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
  stored and returned in UTC.
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

### Roadmap

Ports, repositories and domain rules for these endpoints already exist; the next phase adds the
use cases and routes:

```text
GET/POST       /api/speakers, PUT/DELETE /api/speakers/{id}
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
  `SELECT … FOR UPDATE` on the event row. The registration use case will run in one transaction:
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
- **Development-only Docker setup**: Flask development server with hot reload, migrations on
  start-up. A production setup (WSGI server, `docker-compose.prod.yml`) is out of scope for this
  phase.
