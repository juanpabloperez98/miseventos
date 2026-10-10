# Mis Eventos — Frontend

Web client for **Mis Eventos**, built with Angular. It consumes the backend REST API
([`../back`](../back/README.md)).

> **Status.** Implemented: event catalog with server-side search and pagination, event detail with
> sessions, event creation/editing/deletion according to permissions, sign-up, sign-in and sign-out
> with JWT, session management with speaker assignment, event registration from the detail page, a
> profile with the user's registrations, event cover images uploaded directly to Cloudinary and
> delivered as optimized responsive variants, an in-memory data cache for the catalog and the
> speakers, and dates shown in Colombia time (see [Roadmap](#roadmap)).

## Tech stack

| Concern         | Choice                                                              |
| --------------- | ------------------------------------------------------------------- |
| Framework       | Angular 20.3 (standalone components, no `zone.js` — zoneless)       |
| Language        | TypeScript 5.9 in strict mode (`strict` + `strictTemplates`)        |
| State           | Angular signals; RxJS for asynchronous/HTTP streams and the cache   |
| Styles          | SCSS with design tokens and the system font stack                   |
| Build           | Angular CLI (`@angular/build:application`, esbuild)                 |
| Unit tests      | Karma + Jasmine (default runner of Angular CLI 20)                  |
| Static analysis | ESLint 9 + `angular-eslint` (includes template accessibility rules) |
| Formatting      | Prettier (`eslint-config-prettier` disables conflicting lint rules) |
| Images          | Cloudinary (signed direct upload, `f_auto`/`q_auto` delivery)       |
| Runtime         | Nginx 1.28 serving the production build (Docker)                    |

No extra runtime dependencies are used for state management, dates or images: the cache is built
with RxJS, dates with `Intl`, and Cloudinary is called through `HttpClient` (there is no Cloudinary
SDK in the frontend).

## Requirements

- Node.js `^20.19.0`, `^22.12.0` or `>=24` (developed with Node 22.17 and npm 10.9).
- Google Chrome or Chromium to run the tests (Karma uses headless Chrome).
- The backend running so the API can be consumed (by default at `http://localhost:5000`).

There is no need to install the Angular CLI globally: the scripts use the project's local version.

## Getting started

```bash
cd front
npm install
npm start            # ng serve → http://localhost:4200
```

For the browser to call the API from `http://localhost:4200`, the backend must include that origin
in its `CORS_ORIGINS` variable (see `back/.env.example`). CORS is configured **only** in the
backend.

Image uploads need the Cloudinary credentials in `back/.env` (see `back/README.md`, section
"Event images (Cloudinary)"). The frontend needs no Cloudinary configuration: the backend returns
the signed upload parameters, and the delivery URLs are built from each image's `secure_url`.
Without those credentials the backend answers 503 to upload requests and the rest of the
application keeps working.

### Docker

`front/Dockerfile` is a multi-stage build: it compiles the application (`npm ci` + `npm run build`
on `node:22.17-alpine`) and serves only `dist/mis-eventos/browser` with `nginx:1.28-alpine` (no
Node.js, sources or `node_modules` in the final image). The Nginx configuration
(`nginx/default.conf.template`) applies the SPA fallback to `index.html` and forwards `/api/` to the
backend over the Docker network, so the production build (`apiUrl: '/api'`) does not need CORS.
The full stack is started from the repository root; see the [root README](../README.md).

```bash
docker compose up -d --build frontend    # from the repository root: only the frontend, at http://localhost:4200
```

The Nginx container is configured with environment variables, rendered into the template by the
official image entrypoint (`envsubst`) when the container starts:

| Variable           | Default               | Description                                                              |
| ------------------ | --------------------- | ------------------------------------------------------------------------ |
| `BACKEND_UPSTREAM` | `http://backend:5000` | Upstream of the `/api/` proxy, resolved per request through Docker's DNS |
| `HTTPS_REDIRECT`   | `0`                   | `1` redirects requests that an external TLS proxy reports as plain HTTP  |
| `HSTS_HEADER`      | `""` (disabled)       | `Strict-Transport-Security` value, sent only on HTTPS responses          |

The published host port is `FRONTEND_HOST_PORT` (repository root `.env`, default `4200`, mapped to
port 80 of the container). This container is part of the development stack only: in production the
build (`npm run build` → `dist/mis-eventos/browser/`) is served by Nginx installed on the server.

**Nginx responses** (`nginx/default.conf.template`, `nginx/security-headers.conf`):

- Hashed build artifacts (`*-XXXXXXXX.js`, `*-XXXXXXXX.css`):
  `Cache-Control: public, max-age=31536000, immutable`.
- Everything else, including `index.html` and the files of `public/`: `Cache-Control: no-cache`,
  so a new deployment is picked up immediately.
- `gzip` for text, CSS, JavaScript, JSON and SVG responses of at least 1 KB.
- Security headers on every location: `Content-Security-Policy`, `X-Content-Type-Options`,
  `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` and, optionally,
  `Strict-Transport-Security`. The CSP allows `img-src 'self' data: blob: https://res.cloudinary.com`
  and `connect-src 'self' https://api.cloudinary.com` for the Cloudinary images and uploads.
- There is no proxy cache for `/api/` responses.

## Scripts

| Command                | Description                                         |
| ---------------------- | --------------------------------------------------- |
| `npm start`            | Development server with hot reload.                 |
| `npm run build`        | Production build in `dist/mis-eventos/browser/`.    |
| `npm run build:dev`    | Development build (not minified, with source maps). |
| `npm run watch`        | Development build in watch mode.                    |
| `npm test`             | Unit tests in watch mode (opens Chrome).            |
| `npm run test:ci`      | Unit tests, run once in headless Chrome (for CI).   |
| `npm run lint`         | Static analysis with ESLint (`ng lint`).            |
| `npm run format`       | Formats the project with Prettier.                  |
| `npm run format:check` | Checks the formatting without modifying files.      |

## Folder structure

```text
front/
├── nginx/                      # default.conf.template (server, proxy, cache) + security-headers.conf
├── public/                     # Static files copied as they are
│   ├── favicon.ico, logo_mis_eventos.ico, logo_mis_eventos.png
│   └── images/event-cover-default.svg   # Default event cover (local, no Cloudinary)
├── src/
│   ├── app/
│   │   ├── core/               # Singleton infrastructure
│   │   │   ├── auth/           # AuthService, AuthorizationService (permissions), TokenStorage,
│   │   │   │                   # SessionExpiryRedirect, models
│   │   │   ├── config/         # API_URL
│   │   │   ├── guards/         # authGuard, eventManagerGuard, canManageEventsMatch, guestGuard
│   │   │   ├── http/           # Normalization and translation of API errors
│   │   │   ├── interceptors/   # authInterceptor (Bearer only towards the API)
│   │   │   └── services/       # FlashMessageService (one-time notice between pages)
│   │   ├── shared/             # Reusable, with no business logic
│   │   │   ├── components/     # button, form-field, date-time-input, loading, empty-state,
│   │   │   │                   # error-state, alert, pagination, state-panel (shared styles)
│   │   │   ├── pipes/          # appDate, dateRange, responsiveImage
│   │   │   └── utils/          # request-state, request-cache, date-time, cloudinary-image,
│   │   │                       # validators, validation-messages, forms
│   │   ├── layout/
│   │   │   ├── components/     # site-header (responsive navigation and session), site-footer
│   │   │   └── layouts/main-layout/
│   │   ├── features/           # One folder per feature, lazy loaded
│   │   │   ├── events/
│   │   │   │   ├── index.ts    # Public API of the feature (EventCard, EventModel, EventStatus)
│   │   │   │   ├── events.routes.ts
│   │   │   │   ├── models/     # EventModel, EventImage, EventPage, EventSession, Speaker, status rules
│   │   │   │   ├── services/   # EventsService, SessionsService, SpeakersService, EventImagesService
│   │   │   │   ├── components/ # event-card, event-form, event-image-field, event-status-badge,
│   │   │   │   │               # session-list, session-form, registration-panel
│   │   │   │   └── pages/      # event-list, event-detail, event-create, event-edit, session-form
│   │   │   ├── auth/
│   │   │   │   ├── auth.routes.ts
│   │   │   │   └── pages/      # login, register
│   │   │   ├── profile/
│   │   │   │   ├── profile.routes.ts
│   │   │   │   └── pages/      # profile-page
│   │   │   ├── registrations/  # RegistrationsService (register, my registrations) + index.ts
│   │   │   ├── forbidden/      # «Acceso denegado» (access denied) page + index.ts
│   │   │   └── not-found/
│   │   │       └── pages/not-found-page/
│   │   ├── app.ts              # Root component: only contains <router-outlet />
│   │   ├── app.config.ts       # Global providers (router, HttpClient, zoneless, locale, session restore)
│   │   └── app.routes.ts       # Root route tree
│   ├── environments/
│   │   ├── environment.model.ts        # Interface shared by every environment
│   │   ├── environment.ts              # Production (default)
│   │   └── environment.development.ts  # Development (replaced through fileReplacements)
│   ├── styles/
│   │   ├── _variables.scss     # Tokens: colors, typography, spacing, radii, shadows, breakpoints
│   │   ├── _mixins.scss        # respond-to, container, focus-ring, visually-hidden, form-control
│   │   └── _global.scss        # Custom properties, light reset, base typography, accessibility
│   ├── testing/                # Test utilities (excluded from the application build)
│   ├── styles.scss             # Entry point of the global styles
│   ├── index.html
│   ├── index.spec.ts           # Checks the favicon declared in index.html
│   └── main.ts
├── Dockerfile
├── angular.json
├── eslint.config.js
└── package.json
```

Empty folders are not kept: folders such as `shared/directives` will be created when they contain
real code.

File names follow the Angular 20 style guide: `event-list-page.ts` instead of
`event-list-page.component.ts`, and the class `EventListPage` instead of `EventListPageComponent`.

`AuthService` lives in `core/` (and not in `features/auth`) because the interceptor, the guards and
the layout use it; `features/auth` only contains the pages.

### Responsibilities and dependency rules

- **core/**: singleton infrastructure services (`providedIn: 'root'`), configuration tokens,
  functional guards and interceptors. It contains no UI and no logic of a specific feature.
- **shared/**: visual pieces and utilities **with no business state**. Data services do not go
  here.
- **layout/**: common page structure. It may use `core` and `shared`.
- **features/**: each feature is self-contained. It may depend on `core` and `shared`. It can only
  use another feature through its `index.ts` (public API), never by importing internal paths:
  `profile` uses `EventCard` and `EventModel` from `features/events`. If something becomes generic,
  it moves to `shared` (UI) or `core` (infrastructure).

## Conventions for adding a feature

1. Create the `src/app/features/<feature>/` folder with the structure it needs:

   ```text
   features/events/
   ├── events.routes.ts       # Feature routes (export const EVENTS_ROUTES: Routes)
   ├── pages/                 # Routed components (event-list-page/, event-detail-page/)
   ├── components/            # Presentational components specific to the feature
   ├── services/              # Data access and state (signals) of the feature
   └── models/                # Client-side domain interfaces and types
   ```

2. Generate components with the CLI (already configured with SCSS and `OnPush`):

   ```bash
   npx ng generate component features/events/pages/event-list-page
   ```

3. Register the feature in `app.routes.ts` with lazy loading, inside the layout:

   ```ts
   {
     path: 'events',
     loadChildren: () => import('./features/events/events.routes').then((m) => m.EVENTS_ROUTES),
   },
   ```

   Routes must be declared **before** the `**` wildcard. Each route defines its `title`
   (`'<Página> | Mis Eventos'`, i.e. the page name in Spanish followed by the app name) for
   accessibility and SEO.

4. HTTP services inject `API_URL` instead of importing `environment`:

   ```ts
   private readonly http = inject(HttpClient);
   private readonly apiUrl = inject(API_URL);

   list() {
     return this.http.get<EventPage>(`${this.apiUrl}/events`);
   }
   ```

5. General rules:
   - Standalone components with `ChangeDetectionStrategy.OnPush` (enforced by ESLint).
   - Local state with `signal`/`computed`; RxJS for HTTP and event streams (`toSignal` when the
     template needs it).
   - Forms with typed Reactive Forms (`NonNullableFormBuilder`).
   - Route parameters as `input()` thanks to `withComponentInputBinding()`.
   - Reads that are requested often and do not depend on private data can use `RequestCache`
     (see [State management](#state-management)); the cache key must include whatever changes the
     response (query and session), and successful mutations must clear it.
   - Cloudinary URLs are only built through `shared/utils/cloudinary-image.ts` (or the
     `responsiveImage` pipe), never by hand in components.
   - `*.spec.ts` tests next to the file they test.

## Features and routes

Every page is lazy loaded (`loadChildren` for the `events`, `auth` and `profile` features,
`loadComponent` for each page, including the access denied and 404 pages); only `MainLayout` is part
of the initial bundle.

| Route                                                              | Access                      | Description                                                                                                                             |
| ------------------------------------------------------------------ | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `/` → `/events`                                                    | Public                      | Landing page with search box and paginated catalog (`?page=`, `?search=`); each card shows the event cover                              |
| `/events/:id`                                                      | Public                      | Event detail with its cover and sessions, registration panel; edit/delete according to permissions                                      |
| `/events/new` (alias `/events/create`)                             | ADMIN, ORGANIZER            | Create an event (saved as `DRAFT`), optionally with a cover image. Anonymous → login; no permission → «Acceso denegado» (access denied) |
| `/events/:id/edit`                                                 | ADMIN, owner ORGANIZER      | Edit fields, change the status and replace or remove the cover image                                                                    |
| `/events/:id/sessions/new`, `/events/:id/sessions/:sessionId/edit` | ADMIN, owner ORGANIZER      | Create and edit sessions (anonymous → login; no permission → «Acceso denegado»)                                                         |
| `/auth/login`, `/auth/register`                                    | Anonymous only              | Sign-in and attendee sign-up                                                                                                            |
| `/profile`                                                         | Authenticated (`authGuard`) | User data and the events they are registered to. Without a session → login with `returnUrl=/profile`                                    |
| `/forbidden`, `**`                                                 | —                           | Access denied page (rendered by the guards with `skipLocationChange`) and 404 page                                                      |

### API integration

Only existing backend endpoints are used (`back/README.md`):

| Endpoint                                                                      | Usage                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/events?page&per_page&search`                                        | Catalog. Server-side pagination and search (by name); 9 events per page. Cached for 60 seconds per session and query (`EventsService.list`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `POST /api/events/{id}/sessions`, `GET`/`PUT`/`DELETE /api/sessions/{id}`     | Session management (`SessionsService`): create and edit at `/events/:id/sessions/...` (the form checks that the schedule fits within the event, start < end, and a capacity between 1 and the event capacity, like the backend); delete from the detail page with confirmation (the session is removed from the list without reloading it). The «Sesiones del evento» (event sessions) section is visible to everyone; «Añadir sesión» (add session, also in the empty state), «Editar» (edit) and «Eliminar» (delete) only to ADMIN or the owner ORGANIZER, and only if the event is neither cancelled nor completed. An ADMIN/ORGANIZER who cannot manage them is told why |
| `GET /api/speakers`                                                           | Read-only speaker catalog (`SpeakersService.listAll`, pages of 100, further pages requested in parallel only if there are more than 100). Feeds the «Ponente» (speaker) selector of the session form. Cached for 60 seconds per session                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `GET /api/events/{id}` and `GET /api/events/{id}/sessions`                    | Detail: parallel requests, each with its own loading and error state. Each session includes `speaker_name`, so the detail page shows the speaker without requesting the speaker catalog                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `POST /api/events` / `PUT /api/events/{id}`                                   | Create / edit (there is no `PATCH`). `status` is only sent if it changes. A successful change clears the catalog cache                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `DELETE /api/events/{id}`                                                     | Draft: deleted (204). Published: cancelled (200), and the view is updated with the response. A successful removal clears the catalog cache                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`         | Sign-up (always `ATTENDEE`, followed by an automatic sign-in), JWT and current user                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `POST /api/events/{id}/registrations`                                         | Registration from the detail page (empty body; the user comes from the token). `PUBLISHED` events only. 201 → «Estás inscrito» (you are registered); 409 duplicate → treated as registered; 409 no seats left or not open, 404 → message; 401 → session ends and the user is invited to sign in                                                                                                                                                                                                                                                                                                                                                                              |
| `GET /api/me/registrations`                                                   | Profile, and the detail page for signed-in users (to know whether they are already registered). Returns an array of events (`EventSchema`, the same `EventModel` as the catalog) ordered by start date, including cancelled or completed ones. It includes no registration data of its own (date or status), so the card shows the event status. Never cached                                                                                                                                                                                                                                                                                                                |
| `POST /api/events/{id}/images/upload`, `POST /api/events/{id}/images/confirm` | Cover image upload (`EventImagesService`), see [Images](#images): signed upload parameters, then confirmation of the uploaded `public_id`. A successful confirmation clears the catalog cache                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `DELETE /api/events/{id}/images`                                              | Removes the cover image from the edit page. A successful removal clears the catalog cache                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

The direct upload of the file goes to the `upload_url` returned by the backend
(`https://api.cloudinary.com/v1_1/<cloud_name>/image/upload`), not to the API.

The models in `features/events/models` and `core/auth/auth.models.ts` mirror the backend
marshmallow schemas (`EventModel.image` is an `EventImage` or `null`). Errors shaped as
`{ message, errors: { json: { campo: [...] } } }` (one list of messages per field) are normalized in
`core/http/api-error.ts`: field errors (422) are shown on the matching field, and known messages
(duplicate email, credentials, status transitions, capacity, image service errors...) are
translated.

The list, the detail page and the profile are reloaded when the user changes, because the
visibility of events depends on the user. Only the catalog and the speakers are cached (see
[State management](#state-management)); the event detail, its sessions, the registrations and the
profile are always requested from the API.

### Backend limitations found

- **Search**: by event name only (`search`); there is no search by location or by date.
- **Price and available seats**: the event model has no price nor number of registrations, so the
  cards only show real data.
- **Registrations**: `GET /api/me/registrations` returns events only (no registration date or
  status), and there is no endpoint to cancel a registration, so the interface offers none.
- **Speakers**: the API only exposes a read-only catalog (`GET /api/speakers`); speakers cannot be
  created, edited or deleted from the frontend.

## Authentication, session and permissions

- `AuthService` is the single source of the session state (`user` and `isAuthenticated` signals).
  The user and their role always come from `GET /api/auth/me`; the JWT is never decoded in the
  browser.
- **Token storage**: the backend only accepts `Authorization: Bearer` (it issues no cookies), so the
  token must be readable from JavaScript. It is stored in `sessionStorage` together with its
  `expires_at` (with an in-memory fallback if `sessionStorage` is unavailable):
  - It survives reloads of the tab, is cleared when the tab is closed and is not shared between
    tabs, which limits the exposure compared with `localStorage`.
  - Like any storage readable from JavaScript, it is vulnerable to XSS: the app never inserts
    untrusted HTML (Angular escapes interpolations) and Nginx sends a strict CSP. The safer
    alternative, an `HttpOnly` + `SameSite` cookie, would require backend changes.
  - Expired tokens are discarded, and the session ends automatically when the token expires.
- On start-up, `provideAppInitializer` restores the session (`/auth/me`, with an 8-second timeout)
  before the first navigation. A 401 ends the stored session; a network failure keeps the token so
  a later reload can restore it.
- **Interceptor** (`core/interceptors/auth.interceptor.ts`): adds the token only to URLs that start
  with `API_URL` (never to other domains such as Cloudinary, nor to login or sign-up).
  - **401** with a token: the session is no longer valid and is ended. Since the backend rejects
    invalid tokens even on public endpoints, `GET` requests are retried once without the token;
    mutations return the error to the page. The interceptor itself never redirects (see
    `SessionExpiryRedirect` below), so no loops can happen.
  - **403**: does not end the session; the page states that the user lacks permission.
- **Permissions** centralized in `AuthorizationService`:
  - `canCreateEvents`: ADMIN and ORGANIZER. ATTENDEE and anonymous users do not see the
    «Crear evento» (create event) button.
  - `canManageEvent(ownerId)`: ADMIN manages any event; ORGANIZER only the events they created.
  - The status rules (`isEventEditable`, `removalAction`) live in `events/models`: cancelled or
    completed events show no actions.
- **Authentication before authorization** on `/events/new`, `/events/:id/edit` and the session pages
  (`managerPage()` in `events.routes.ts`):
  1. Anonymous → `/auth/login?returnUrl=<ruta pedida>` (the requested route) and, after signing in,
     back to that route.
  2. Authenticated without permission (ATTENDEE) → «Acceso denegado» (access denied) page at the
     requested URL itself, without ending the session nor redirecting to the login page or the
     catalog.
  3. ADMIN or ORGANIZER → the form.

  The form route only matches if `canManageEventsMatch` allows it; otherwise the router uses a twin
  route with the same URL, protected by `authGuard`, that shows the access denied page.
  `eventManagerGuard` checks the session and the role again on the form route. Ownership of the
  event is checked when it is loaded in the edit page. `guestGuard` keeps authenticated users away
  from login and sign-up. `returnUrl` only accepts internal routes (`safeReturnUrl` in the login
  page rejects absolute and protocol-relative URLs).

- **Event routes**: static routes (`new`) are declared before the id-based ones, and `:id` /
  `:id/edit` only accept numeric ids (`eventIdMatcher`), so a segment such as `create` or `abc` is
  never read as an id nor triggers `GET /events/NaN`: `/events/create` is an alias of `/events/new`
  and anything else shows the 404 page.
- **HTTP 401 versus 403**: a 401 ends the session (and, on a protected route, leads to the login
  page); a 403 keeps it and the page states that the user lacks permission.
- The backend remains the authority: it checks the role (from its database) and the ownership again
  on every request; the interface only avoids offering actions that would fail.

## State management

There is no global store (NgRx or similar): shared state is small and lives in `root` services with
**signals**; the state of each screen is derived from the URL and the API.

| State                                             | Where it lives                                                                                                                                | Used by                            |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| User, session (`user`, `isAuthenticated`)         | `AuthService` (read-only signals)                                                                                                             | Header, guards, permissions, pages |
| Token and its expiry                              | `TokenStorage` (`sessionStorage`), only through `AuthService`                                                                                 | Interceptor                        |
| Permissions (`canCreateEvents`, `canManageEvent`) | `AuthorizationService` (`computed` over the user)                                                                                             | Header, list, detail, edit page    |
| End of session (`logout`, `expired`, `rejected`)  | `AuthService.sessionEnded$` (one emission per session)                                                                                        | `SessionExpiryRedirect`            |
| Message between pages                             | `FlashMessageService` (one-time)                                                                                                              | Destination pages                  |
| List, detail, sessions, profile                   | Each page: `toSignal(toObservable(clave).pipe(switchMap(...)))` (`clave` is the load key) → `RequestState<T>` (`loading`, `success`, `error`) | The page itself                    |
| Catalog pages and speakers                        | `RequestCache` in `EventsService` and `SpeakersService` (60-second TTL)                                                                       | List page, session form            |

Rules that keep the interface consistent:

- **The key of each load includes the user** (in addition to the page, the search or the id). When
  signing in or out, the list, the detail page and the profile request their data again with the
  new identity and show `loading` meanwhile, so data from the previous user is never shown. The
  profile does not query the API without a session.
- **`switchMap` cancels the previous request** if the key changes before it responds (quick page or
  search changes), so an old response can never overwrite a newer one.
- **Transient state** of the detail page (notice, deletion confirmation) is reset when the event or
  the user changes (`linkedSignal`).
- **End of session**:
  - _Logout_: `AuthService` clears the token, the user and any pending messages; the header is
    updated immediately and navigates to the catalog.
  - _Expired token or 401_: in addition, if the active route is protected (`authGuard`,
    `eventManagerGuard`), `SessionExpiryRedirect` sends the user to the login page once, with
    `returnUrl` and a notice. Ending the session is idempotent: several simultaneous 401 responses
    produce a single redirect. The interceptor retries only `GET` requests, once and without the
    token, and the login page makes no authenticated requests, so there are no loops.

### Data cache

`shared/utils/request-cache.ts` (`RequestCache<T>`) is an in-memory cache of GET responses built
with RxJS (`shareReplay({ bufferSize: 1, refCount: true })`):

- **Reuse**: identical requests made while one is in flight share a single HTTP call; a successful
  response is reused for 60 seconds (`EVENT_LIST_CACHE_TTL_MS`, `SPEAKERS_CACHE_TTL_MS`), counted
  from the moment the response arrives.
- **Errors** are never kept: the entry is dropped and the next call retries.
- **Cancellation**: if every subscriber leaves before the response arrives, the request is
  cancelled and the next subscriber starts it again.
- **Cleanup**: expired entries are dropped on every read.
- **Keys and sessions**: the key includes the access token sent with the request (or `anonymous`)
  plus the query parameters, because the catalog depends on the user's role (organizers also see
  their drafts). Responses are never shared between sessions.
- **Invalidation**: creating, editing or removing an event, and confirming or removing a cover
  image, clear the catalog cache (`EventsService.clearListCache()`). Failed mutations keep it.
- **Not cached**: event detail, sessions, registrations, profile and authentication.

This is an application-level cache in memory: it is lost on reload and is unrelated to the browser
HTTP cache, the Cloudinary CDN or any backend cache (the backend has none).

## API URL configuration

The URL is defined with the official Angular CLI environments mechanism:

| File                                          | Used by                          | `apiUrl`                    |
| --------------------------------------------- | -------------------------------- | --------------------------- |
| `src/environments/environment.development.ts` | `npm start`, `npm run build:dev` | `http://localhost:5000/api` |
| `src/environments/environment.ts`             | `npm run build` (production)     | `/api` (same origin)        |

`apiUrl` includes the `/api` prefix used by every backend route. Production uses a relative path,
meant to serve the frontend and the API under the same domain through a reverse proxy; if the API
is published on another domain, changing the value in `environment.ts` is enough.

The value is exposed to the application through the `API_URL` token
(`core/config/api-url.token.ts`), which tests can override with
`{ provide: API_URL, useValue: '...' }`.

### Security

- **Everything in `environment*.ts` ends up in the JavaScript bundle and is public.** Any user can
  read it from the browser. Never include secrets, private keys or tokens. The Cloudinary API
  secret, in particular, only exists in the backend.
- Angular does not read `.env` files at runtime: the application is static code that runs in the
  browser. That is why this project has no `.env.example`; the configuration is set at build time
  with the environment files. The Nginx variables above are read by the container at start-up, not
  by Angular.
- Minification is not a security measure and does not hide information. The code is minified, not
  obfuscated.
- CORS is configured in the backend (`CORS_ORIGINS`), not in the frontend.

## Performance

- **Lazy loading**: each feature and each page is loaded on demand (`loadChildren` /
  `loadComponent`). The root component imports no feature. The build output lists the generated
  _lazy chunks_.
- **Production build** (default `ng build` configuration in `angular.json`): script optimization
  (minification, tree-shaking and dead code elimination), style minification, font optimization,
  hashed file names for long-term caching (`outputHashing: all`), no source maps and size budgets
  (`budgets`: initial bundle warning at 500 kB and error at 1 MB; component styles warning at 4 kB
  and error at 8 kB). Critical CSS inlining is disabled (`inlineCritical: false`).
- **Zoneless + OnPush**: no `zone.js` in the bundle; change detection is based on signals.
- **HTTP**: `provideHttpClient(withFetch(), withInterceptors([authInterceptor]))`. Reads use
  `switchMap`, so a page or search change cancels the previous request. Manual subscriptions use
  `takeUntilDestroyed`; everything else is converted to signals with `toSignal`.
- **Data cache**: the catalog and the speakers are cached for 60 seconds and concurrent identical
  requests are shared (see [Data cache](#data-cache)).
- **Images**: responsive Cloudinary variants with automatic format and quality, lazy loading for
  cards and reserved dimensions to avoid layout shifts (see [Images](#images)).

These optimizations are verified in the code, the configuration and the build output; no
Lighthouse or Web Vitals measurement is recorded.

### Images

- Modern formats (**AVIF** or **WebP**) with dimensions adjusted to where they are used.
- **Event covers (Cloudinary).** URLs are built only in `shared/utils/cloudinary-image.ts` (in
  templates, the `responsiveImage` pipe): `f_auto` (AVIF/WebP when the browser supports them,
  without forcing WebP), `q_auto` and `c_fill,g_auto` with a fixed aspect ratio per use, generated
  on demand by the Cloudinary CDN (only the original is stored). URLs that are not Cloudinary
  deliveries (`https://res.cloudinary.com/.../image/upload/...`) are returned unchanged.

  | Use             | Aspect ratio | Variants (`srcset`)                    |
  | --------------- | ------------ | -------------------------------------- |
  | Card (`card`)   | 16:10        | 400×250 (mobile), 800×500 (2x screens) |
  | Cover (`cover`) | 16:9         | 400×225, 800×450, 1200×675, 1920×1080  |

  The widths follow the reference devices (mobile 400, tablet 800, desktop 1200, high resolution
  1920); the height follows the real aspect ratio of each place so the layout does not shift. Every
  Cloudinary `<img>` declares `srcset`, `sizes`, `width` and `height`; cards use `loading="lazy"` and
  `decoding="async"`, and the detail cover uses `fetchpriority="high"`. `NgOptimizedImage` is not
  used: its Cloudinary _loader_ only varies the width (no crop with a fixed aspect ratio) and would
  require configuring the `cloud_name` in the frontend; `secure_url` is enough.

- **Default cover.** Event cards always show an image: when `image` is `null`, missing or has an
  empty URL, or when the Cloudinary image fails to load, the card shows
  `public/images/event-cover-default.svg` (served at `images/event-cover-default.svg`) without
  `srcset`. If the default image also fails, nothing else is tried, so there is no error loop. The
  event data is never modified. The cover box keeps a 16:10 ratio with `object-fit: cover`, and
  shows the brand gradient while the image loads. The detail page has no fallback: it only renders
  the cover when the event has one.
- **Upload.** `EventImagesService` requests the signature from the backend (only name, type and
  size), sends the file directly to Cloudinary and confirms the `public_id`; the interceptor never
  adds the JWT to Cloudinary requests. The image picker of the event form (`event-image-field`)
  first validates the type (JPG, PNG, WebP) and the size (5 MB, the same limits as the backend),
  shows a local preview (`blob:`) and the status of each stage, and lets the user discard a new
  file, remove the current image or keep it. Submission is blocked while the upload lasts. The image
  is uploaded after the event is saved (creating it requires its id):
  - On creation, if the upload fails, the event is kept and the detail page explains that the image
    can be added from the edit page.
  - On editing, if the upload fails, the user stays on the edit page with an error and can retry.
  - Each stage reports its own error (validation, authorization, upload, confirmation, removal).
  - Leaving the page cancels the upload in progress.
  - With `withFetch()`, Angular does not report upload progress, so the status shows no percentage.

  The backend keeps the previous cover until the new one is confirmed. The upload flow is covered
  by unit tests with mocked HTTP; it has not been verified against a real Cloudinary account.

- The Nginx CSP allows `img-src https://res.cloudinary.com blob:` and
  `connect-src https://api.cloudinary.com`.
- Simple icons and logos, preferably as SVG.
- Project static files go in `public/`; do not commit large images to the repository.

## UI foundations

### Design tokens

Tokens are defined in `src/styles/_variables.scss` and published as _custom properties_ on
`:root`. Components consume them with `var(--token)`:

| Group      | Examples                                                                                                      |
| ---------- | ------------------------------------------------------------------------------------------------------------- |
| Colors     | `--color-primary` (violet), `--color-secondary` (blue), `--gradient-brand`, `--color-text`, `--color-surface` |
| States     | `--color-success`, `--color-warning`, `--color-danger`, `--color-info` (+ `-subtle` variants)                 |
| Typography | `--font-size-sm` … `--font-size-4xl`, `--font-weight-*`, `--line-height-*`                                    |
| Spacing    | `--space-1` (4px) … `--space-8` (64px)                                                                        |
| Borders    | `--border-width`, `--radius-sm/md/lg/xl/full`, `--shadow-sm/md/lg`                                            |

The breakpoints (`sm` 576px, `md` 768px, `lg` 1024px, `xl` 1280px) are Sass values because media
queries do not support custom properties. In components:

```scss
@use 'mixins' as mx;

.grid {
  display: grid;

  @include mx.respond-to(md) {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

`src/styles` is registered in `stylePreprocessorOptions.includePaths`, so relative paths are not
needed. The design is _mobile first_: the event grids (catalog and profile) go from one column to two
(`sm`) and three (`lg`), forms from one column to two (`md`), and the header collapses into a menu button below
`md`. The `form-control` mixin gives text inputs, selects and the date-time picker the same
look.

The styles are verified in the code; there is no automated visual or cross-device test.

### Accessibility

- "Saltar al contenido principal" (skip to main content) link, semantic landmarks (`header`, `nav`,
  `main`, `footer`) and `lang="es"`.
- Visible focus with `:focus-visible` (`focus-ring` mixin); never remove the `outline` without an
  alternative.
- Text colors with WCAG AA contrast.
- `prefers-reduced-motion` respected globally.
- Document title per route and `angular-eslint` accessibility rules in templates
  (`templateAccessibility`).
- Form errors linked with `aria-describedby`/`aria-invalid`; the header menu button uses
  `aria-expanded`/`aria-controls`; pagination uses `aria-current="page"`; after a page change the
  focus moves to the results heading.

### UI state conventions

Implemented in `shared/components/` (`app-loading`, `app-empty-state`, `app-error-state`,
`app-alert`) and in `shared/utils/request-state.ts` (`RequestState<T>`: `loading | success | error`):

| State        | Guideline                                                                                                                                                  |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Loading      | `app-loading`: spinner and text with `role="status"`. Do not block the whole page. Buttons of an operation in progress show a spinner and set `aria-busy`. |
| Empty        | Clear message with the reason and, where relevant, an action to leave the empty state.                                                                     |
| Error        | `role="alert"`, `--color-danger` / `--color-danger-subtle` colors, an understandable message and an option to retry.                                       |
| Confirmation | `role="status"` (non-intrusive notice) with `--color-success` / `--color-success-subtle`. Destructive actions ask for explicit confirmation.               |

Templates use the built-in control flow (`@if`, `@for`, `@switch`, `@let`) to render these states.

### Shared components

| Component                                                        | Usage                                                                                                                                                  |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `button[appButton]`, `a[appButton]`                              | `primary/secondary/ghost/danger/inverse` variants, size and `loading` (spinner + `aria-busy`). Keeps the native semantics                              |
| `app-form-field`                                                 | Label, control (`text`, `email`, `password`, `number`, `datetime`, `textarea`, `select`), hint and error linked with `aria-describedby`/`aria-invalid` |
| `app-date-time-input`                                            | Native date input plus hour (1–12), minutes and AM/PM selects; used by `app-form-field type="datetime"`                                                |
| `app-pagination`                                                 | Server-side pagination: emits the requested page; the state lives in the URL                                                                           |
| `app-loading`, `app-empty-state`, `app-error-state`, `app-alert` | UI states                                                                                                                                              |

### Dates and times

All the date and time logic lives in `shared/utils/date-time.ts` (no dependencies, built on
`Intl`):

- They are always shown in Colombia time (`America/Bogota`) and with the `es-CO` locale (also the
  application `LOCALE_ID`), whatever the device timezone. Hours are never added or subtracted by
  hand: the offset comes from the browser's timezone database.
- Formats: date `dd/MM/yyyy` (`10/10/2026`), time `h:mm a` (`2:45 PM`) and date and time
  `dd/MM/yyyy, h:mm a`. In templates: `value | appDate: 'date' | 'time' | 'datetime'` and
  `start | dateRange: end`. Angular's `date` pipe is not used, because it depends on the device
  timezone.
- The API exchanges ISO 8601 instants (the backend answers in UTC). Forms edit the Colombia time
  (`toColombiaInput` / `fromColombiaInput`) and send a UTC instant back.
- Civil dates without a time (`2026-10-10`) are not converted between timezones, so they do not
  change day.
- `app-form-field type="datetime"` uses `app-date-time-input`: a native date input plus hour,
  minutes and AM/PM selects, because `datetime-local` and `time` follow the browser settings and
  may show the 24-hour clock. The control value is still `yyyy-MM-ddTHH:mm`. The native date input
  itself still displays the date in the browser's format.

## Tests

`npm run test:ci` runs the unit tests in headless Chrome. They use the real `HttpClient` with the
interceptor against `HttpTestingController`, and the real router (`RouterTestingHarness`);
`src/testing/test-helpers.ts` signs in through the real `AuthService` by answering `/auth/login`
and `/auth/me`, and provides fixtures (`buildEvent`, `buildSession`, `buildImage`, `imageFile`) and
helpers that interact like a user (`fillDateTime`, `selectFile`). No test calls the real backend
or Cloudinary.

The `*.spec.ts` files cover:

- **Pages**: list (loading, cards and cover images, empty state, error and retry, pagination and
  search in the URL), detail (sessions, cover, 404, actions according to role and ownership, delete
  and cancel, registration, Colombia time), create (with and without image, image failure), edit
  (ownership, `PUT`, 409 conflicts, image replacement, removal and failure), session form page and
  profile.
- **Components**: event form (validations, payload, server errors, double submission, schedule in
  Colombia time), session form, event card (default cover and load error fallback), image picker,
  date-time input and pagination.
- **Services**: `EventsService` (including the catalog cache), `SpeakersService` (cache),
  `SessionsService`, `RegistrationsService` and `EventImagesService` (authorization, direct upload
  without the JWT, confirmation, errors per stage, cancellation, removal).
- **Core**: `AuthService`, `AuthorizationService`, session expiry redirect, interceptor (domains,
  401, 403), guards, routes (`app.routes`, `events.routes`) and API error translation.
- **Utilities**: `RequestCache` (reuse, expiry, errors, cancellation, invalidation),
  `cloudinary-image` (transformations, variants), `date-time` and the date pipes, and the favicon
  declared in `index.html` (`src/index.spec.ts`).

Test coverage is not measured (no script runs `--code-coverage`), and there are no end-to-end
tests. Validation commands:

```bash
npm run test:ci        # unit tests
npm run lint           # ESLint
npm run format:check   # Prettier
npm run build          # production build (fails if a budget is exceeded)
```

On Windows with `core.autocrlf=true`, Git checks files out with CRLF line endings while Prettier
expects LF, so `npm run format:check` can report files whose only difference is the line ending.

## Roadmap

Not implemented yet, or possible improvements:

- Speaker management (create, edit, delete): out of scope; sessions assign existing speakers
  through `GET /api/speakers`.
- The backend does not report available seats nor the registration date in
  `GET /me/registrations`; the detail page queries that list to know whether the user is already
  registered.
- Catalog filter by status for organizers (`?status=` already exists in the API and in
  `EventQuery`, but the list page does not use it).
- A default cover (and load error fallback) on the event detail page, like the cards.
- Upload progress percentage (it would require the XHR backend of `HttpClient` instead of
  `withFetch()`).
- Measured test coverage, end-to-end tests and a CI pipeline running the validation commands.
- A `.gitattributes` file enforcing LF line endings, so `format:check` behaves the same on every
  platform.
- A visual check of the responsive layout and a real upload to a Cloudinary account.
