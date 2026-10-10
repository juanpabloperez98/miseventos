# Mis Eventos

Event management platform: a Flask REST API ([`back/`](back/README.md)), an Angular web client
([`front/`](front/README.md)) and PostgreSQL, orchestrated with Docker Compose.

```text
                  browser
                    │  http://localhost:4200
                    ▼
        ┌──────────────────────────┐
        │ frontend (Nginx)         │  compiled Angular + proxy /api/ → backend:5000
        └────────────┬─────────────┘
                     │  Docker network "miseventos"
        ┌────────────▼─────────────┐
        │ backend (Flask)          │  dev: Flask --debug · prod: Gunicorn
        └────────────┬─────────────┘
        ┌────────────▼─────────────┐
        │ postgres:17-alpine       │  named volume postgres_data
        └──────────────────────────┘
```

| File                                                    | Contents                                                                   |
| ------------------------------------------------------- | -------------------------------------------------------------------------- |
| `docker-compose.yml`                                    | Full stack in **development** mode (default configuration)                 |
| `docker-compose.prod.yml`                               | **Production**: backend (Gunicorn) + PostgreSQL only                       |
| `back/Dockerfile`, `back/scripts/start.sh`              | Backend image: migrations → seeder (development only) → server             |
| `front/Dockerfile`, `front/nginx/default.conf.template` | Angular built with Node and served by Nginx (SPA fallback and `/api/` proxy) |

## Requirements

- Docker Engine with Docker Compose v2.24 or later (the overrides use `!reset`).
- Only for frontend development outside Docker: Node.js 22 (see [`front/README.md`](front/README.md)).

## Initial setup

```bash
cp .env.example .env              # PostgreSQL credentials and published ports
cp back/.env.example back/.env    # Backend settings (JWT, CORS, seeders...)
```

Edit both files and replace the example values (passwords, a `JWT_SECRET_KEY` of at least 32
characters, `SEED_*` passwords). The `.env` files are excluded from Git and from the Docker images
(`.gitignore` and `back/.dockerignore`).

| Variable (root `.env`)                              | Purpose                                                                       | Default        |
| --------------------------------------------------- | ----------------------------------------------------------------------------- | -------------- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | PostgreSQL credentials; Compose uses them to build the backend `DATABASE_URL` | — (required)   |
| `POSTGRES_HOST_PORT`                                | PostgreSQL port on the host (development only)                                | `5432`         |
| `BACKEND_HOST_PORT`                                 | API port on the host (development only)                                       | `5000`         |
| `FRONTEND_HOST_PORT`                                | Port of the Nginx frontend on the host                                        | `4200`         |

The backend variables (`FLASK_ENV`, `JWT_SECRET_KEY`, `JWT_EXPIRATION_MINUTES`, `CORS_ORIGINS`,
`LOG_LEVEL`, `SEED_*`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`) are described in
`back/.env.example` and in [`back/README.md`](back/README.md#environment-variables).

**The frontend has no secrets.** Its only setting is `apiUrl`, which is fixed at build time
(`front/src/environments/`) and is public: in production it is `/api` (a relative path to the Nginx
proxy). Changing container variables does not modify the bundle that is already built; the only
variable of the frontend container is `BACKEND_UPSTREAM`, the target of the proxy inside the Docker
network (`http://backend:5000` by default).

## Running the full stack

### Development (default)

```bash
docker compose up -d --build
docker compose ps        # the three services must show as (healthy)
```

| Service                                           | URL                                                                 |
| ------------------------------------------------- | ------------------------------------------------------------------- |
| Frontend (Nginx, Angular production build)        | <http://localhost:4200>                                             |
| Direct API                                        | <http://localhost:5000/api>                                         |
| Backend health                                    | <http://localhost:5000/health>                                      |
| Swagger UI / OpenAPI                              | <http://localhost:5000/docs> · <http://localhost:5000/openapi.json> |
| PostgreSQL                                        | `localhost:5432`                                                    |

In development the backend mounts `./back` and uses the Flask server with hot reload; on start-up it
applies the migrations and runs the idempotent seeder (it never duplicates data). The frontend
container always serves the optimized build through Nginx; for hot reload use `npm start` (next
section).

### Production

`docker-compose.prod.yml` is standalone (it is **not** applied on top of `docker-compose.yml`) and
only runs the backend with Gunicorn and PostgreSQL. The frontend is not part of it: its static build
is served by an Nginx installed on the server, which forwards `/api/` to `127.0.0.1:5001` (server
configuration outside this repository).

Configuration on the server (files ignored by Git):

| File                                          | Variables                                                                                                                                                                  |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.env` (root, template `.env.example`)        | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (required: Compose fails if they are missing); `BACKEND_ENV_FILE` optional. The port is fixed (`127.0.0.1:5001`)        |
| `back/.env` (or the one in `BACKEND_ENV_FILE`) | `JWT_SECRET_KEY` (required), `CORS_ORIGINS`, `JWT_EXPIRATION_MINUTES`, `LOG_LEVEL`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `CLOUDINARY_*`, `EVENT_IMAGE_MAX_BYTES`        |

- Replace every example value (`change-me`, `replace-with-...`). `POSTGRES_PASSWORD` is inserted
  into `DATABASE_URL` without URL-encoding: use only letters, digits, `-` and `_`
  (`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`).
- `docker-compose.prod.yml` sets `FLASK_ENV=production`, `DATABASE_URL` and `SEED_*_ENABLED=false`,
  overriding whatever `back/.env` says.
- If the frontend is served on the same domain as `/api/`, leave `CORS_ORIGINS` empty.

```bash
docker compose -f docker-compose.prod.yml config --quiet     # validates the file and the variables
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps                 # both services (healthy)
curl -fsS http://127.0.0.1:5001/health
```

**Migrations.** On every start, `back/scripts/start.sh` validates the settings, runs
`alembic upgrade head` (forward only) and then starts Gunicorn; on the first deployment it creates
the schema. For an update that includes migrations, back up the database first and apply them
explicitly before replacing the backend:

```bash
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.prod.yml up -d backend
docker compose -f docker-compose.prod.yml exec backend alembic current
```

If a migration fails, PostgreSQL rolls back the transaction and the running backend is not
affected; if it failed during a start-up, the container would restart in a loop until it is fixed
(see `docker compose -f docker-compose.prod.yml logs backend`).

Differences from development:

|                 | Development                                              | Production                                                                                             |
| --------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Backend         | Flask `--debug`, mounted source code, dev dependencies   | Gunicorn, `miseventos-backend:prod` image without dev dependencies or mounted source code              |
| `FLASK_ENV`     | The value in `back/.env`                                 | `production` (forced by `docker-compose.prod.yml`)                                                     |
| Seeder          | Runs on every start (idempotent)                         | Forbidden: `SEED_*_ENABLED` forced to `false`, and the backend does not start if any of them is `true` |
| `JWT_SECRET_KEY`| At least 32 characters                                   | Also: no example placeholders and at least 16 distinct characters, or the backend does not start       |
| Published ports | 4200, 5000, 5432                                         | Only 5000 on `127.0.0.1` (for the host Nginx); PostgreSQL is only reachable on an internal network     |

See [Production security](#production-security) before a real deployment.

## Production security

### Backend settings and `JWT_SECRET_KEY`

Use a settings file of your own on the server, outside the repository, and point to it with
`BACKEND_ENV_FILE` in the root `.env` (default `./back/.env`):

```bash
# Generate a different key per environment and store it only in that file or in your secrets manager.
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

- The backend validates its settings **before running the migrations** (`back/scripts/start.sh`).
  In production it refuses to start if `JWT_SECRET_KEY` is missing, has fewer than 32 characters,
  contains an example value (`replace-with`, `change-me`) or has fewer than 16 distinct characters.
  Error messages never show the key.
- The key is not generated automatically: it must be stable, because changing it invalidates every
  issued token.
- In development 32 characters are enough; the value in `back/.env.example` is fine for testing.
- Also change `POSTGRES_PASSWORD`, and never publish the `.env` files (they are listed in
  `.gitignore` and in the `.dockerignore` files).

### Seeders

- `docker-compose.prod.yml` forces `SEED_ADMIN_ENABLED`, `SEED_ORGANIZER_ENABLED`,
  `SEED_ATTENDEE_ENABLED` and `SEED_DEMO_DATA_ENABLED` to `false`.
- If any of them is `true` with `FLASK_ENV=production`, the backend (and any `flask` command) fails
  on start-up with `Seeding must be disabled in production`, without touching the database.
- `start.sh` does not run the seeder in production, and the `seed-initial-data` command also refuses
  to run if it is launched by hand.

### HTTPS

In production, HTTPS is terminated by the server's Nginx, which is configured outside this
repository.

What follows applies to the **dockerized** frontend (`front/Dockerfile`), which is now only part of
the development stack, if it is published behind an **external TLS terminator** (a reverse proxy or
the provider's load balancer) in front of the frontend port.

1. The external proxy terminates TLS, forwards to `http://<servidor>:${FRONTEND_HOST_PORT}`
   (`<servidor>` being the server host) and sets the `X-Forwarded-Proto` header (overwriting the
   client's value).
2. Nginx keeps that `X-Forwarded-Proto` when it forwards `/api/` to the backend.
3. Variables of the frontend container (`ENV` in `front/Dockerfile`, which can be overridden in the
   `environment` block of the `frontend` service):

   | Variable           | Effect                                                                                                                                                                                       | Default            |
   | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
   | `HTTPS_REDIRECT=1` | Redirects with `301` to `https://` the requests that the proxy marks as `X-Forwarded-Proto: http`. Requests without that header (health checks, internal traffic) are not redirected, so there are no loops | `0`                |
   | `HSTS_HEADER`      | Value of `Strict-Transport-Security`, sent only on responses served over HTTPS                                                                                                               | empty (disabled)   |

   Enable `HTTPS_REDIRECT` only behind a proxy that controls `X-Forwarded-Proto`. Start with
   `HSTS_HEADER=max-age=300` and increase the value (and add `includeSubDomains`) only once HTTPS
   works on every affected host.

4. The backend generates no absolute URLs, redirects or cookies, so it does not need to know the
   original scheme (`ProxyFix` is not used).

Pending for a real deployment: domain, certificate and the proxy or load balancer with TLS.

### Frontend headers

Nginx sends `Content-Security-Policy` (`script-src 'self'`, `connect-src 'self'`,
`frame-ancestors 'none'`; `style-src` allows inline styles because Angular inserts the component
styles), `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and `Permissions-Policy`
(`front/nginx/security-headers.conf`). The production build does not use Angular's critical CSS
inlining, which requires an inline `onload` handler that is incompatible with this CSP.

## Frontend in development mode (hot reload)

Start only the database and the API, and run Angular on the host:

```bash
docker compose up -d postgres backend
cd front
npm install
npm start               # http://localhost:4200 → calls http://localhost:5000/api (CORS_ORIGINS)
```

`npm start` uses port 4200, the same as the `frontend` container: if that container is running,
stop it with `docker compose stop frontend` or change `FRONTEND_HOST_PORT` in `.env`.

To start **only the dockerized frontend**: `docker compose up -d --build frontend`. Nginx serves the
application even if the backend is not available; calls to `/api/` return `502` until it is, and
the interface shows its error state with a retry option.

## Tests

```bash
# Backend (inside the development container). Integration tests use TEST_DATABASE_URL
# (database <POSTGRES_DB>_test, created automatically), never the development database.
docker compose exec backend pytest                         # unit + integration
docker compose exec backend pytest tests/unit              # unit tests only
docker compose exec backend pytest tests/integration       # database, HTTP and CLI
docker compose exec backend ruff check . && docker compose exec backend ruff format --check .
docker compose exec backend mypy
docker compose exec backend alembic check                  # models and migrations match

# Frontend (on the host)
cd front
npm run lint
npm run test:ci
npm run build
```

## Operations

```bash
docker compose ps                         # container status and health
docker compose logs -f                    # logs of every service
docker compose logs -f backend            # logs of one service
docker inspect --format '{{json .State.Health}}' miseventos-backend-1   # health check details

docker compose up -d --build              # rebuild images and recreate whatever changed
docker compose build --no-cache frontend  # rebuild an image from scratch
docker compose restart backend            # restart a service

docker compose stop                       # stop without removing containers
docker compose down                       # remove containers and network; data is kept
```

For the production stack, use `docker compose -f docker-compose.prod.yml` in every command; its
volume is `miseventos-prod_postgres_data`.

PostgreSQL data lives in the named volume `miseventos_postgres_data` and survives `stop`, `down` and
container re-creation. **`docker compose down -v` deletes the volume and all the data**; use it only
if you want to start from scratch.

### Health checks

| Service    | Check                                                                     |
| ---------- | ------------------------------------------------------------------------- |
| `postgres` | `pg_isready` (defined in `docker-compose.yml`)                            |
| `backend`  | `GET /health` from inside the container (defined in `back/Dockerfile`)    |
| `frontend` | Nginx serves `index.html` (defined in `front/Dockerfile`)                 |

The backend waits for PostgreSQL to be `healthy` before starting (`depends_on`). That only orders
the start-up: if the database restarts later, the backend keeps running and recovers its
connections on the following requests. The frontend depends on no other service. All of them use
`restart: unless-stopped`.

## Nginx `/api/` proxy

- The browser always calls relative paths (`/api/...`), so it needs neither CORS nor the `backend`
  name, which only exists inside the Docker network.
- Nginx forwards the URI unchanged (backend routes already start with `/api`), together with the
  method, the body, the `Authorization` header and the `X-Forwarded-*` headers.
- The backend name is resolved on every request through Docker's internal DNS, so Nginx starts even
  if the backend is not ready and keeps working if the backend container is re-created.
- Angular routes (`/events/2`, `/auth/login`...): `try_files` returns `index.html`, so they can be
  opened or reloaded directly. Hashed assets are served with a one-year cache and `index.html` with
  no cache.
