# Mis Eventos — Frontend

Cliente web de **Mis Eventos**, construido con Angular. Consume la API REST del backend
([`../back`](../back/README.md)).

> **Estado.** Implementados: catálogo de eventos con búsqueda y paginación del servidor, detalle con
> sesiones, creación/edición/eliminación de eventos según permisos, registro, inicio y cierre de sesión
> con JWT, gestión de sesiones con asignación de ponente, inscripción a eventos desde el detalle y
> perfil con las inscripciones del usuario (ver [Pendiente](#pendiente-para-próximas-fases)).

## Stack

| Aspecto           | Elección                                                          |
| ----------------- | ----------------------------------------------------------------- |
| Framework         | Angular 20.3 (componentes standalone, sin `zone.js` — zoneless)   |
| Lenguaje          | TypeScript 5.9 en modo estricto (`strict` + `strictTemplates`)    |
| Estado            | Signals de Angular; RxJS para flujos asíncronos/HTTP              |
| Estilos           | SCSS con tokens de diseño y fuente del sistema                    |
| Build             | Angular CLI (`@angular/build:application`, esbuild)               |
| Pruebas unitarias | Karma + Jasmine (runner por defecto de Angular CLI 20)            |
| Análisis estático | ESLint 9 + `angular-eslint` (incluye reglas de accesibilidad)     |
| Formato           | Prettier (`eslint-config-prettier` desactiva reglas en conflicto) |

## Requisitos previos

- Node.js `^20.19.0`, `^22.12.0` o `>=24` (desarrollado con Node 22.17 y npm 10.9).
- Google Chrome o Chromium para ejecutar las pruebas (Karma usa Chrome headless).
- El backend en ejecución para consumir la API (por defecto en `http://localhost:5000`).

No es necesario instalar Angular CLI globalmente: los scripts usan la versión local del proyecto.

## Puesta en marcha

```bash
cd front
npm install
npm start            # ng serve → http://localhost:4200
```

Para que el navegador pueda llamar a la API desde `http://localhost:4200`, el backend debe incluir ese
origen en su variable `CORS_ORIGINS` (ver `back/.env.example`). CORS se configura **solo** en el
backend.

### Docker

`front/Dockerfile` compila la aplicación (`npm ci` + `npm run build` en `node:22.17-alpine`) y sirve
solo `dist/mis-eventos/browser` con `nginx:1.28-alpine`. La configuración de Nginx
(`nginx/default.conf.template`) aplica el fallback de la SPA a `index.html` y reenvía `/api/` al
backend por la red de Docker, por lo que el build de producción (`apiUrl: '/api'`) no necesita CORS.
El stack completo se levanta desde la raíz del repositorio; ver el [README principal](../README.md).

```bash
docker compose up -d --build frontend    # desde la raíz: solo el frontend en http://localhost:4200
```

## Scripts

| Comando                | Descripción                                                  |
| ---------------------- | ------------------------------------------------------------ |
| `npm start`            | Servidor de desarrollo con recarga en caliente.              |
| `npm run build`        | Build de producción en `dist/mis-eventos/browser/`.          |
| `npm run build:dev`    | Build de desarrollo (sin minificar, con source maps).        |
| `npm run watch`        | Build de desarrollo en modo observación.                     |
| `npm test`             | Pruebas unitarias en modo observación (abre Chrome).         |
| `npm run test:ci`      | Pruebas unitarias una sola vez en Chrome headless (para CI). |
| `npm run lint`         | Análisis estático con ESLint (`ng lint`).                    |
| `npm run format`       | Formatea el proyecto con Prettier.                           |
| `npm run format:check` | Verifica el formato sin modificar archivos.                  |

## Estructura de directorios

```text
front/
├── public/                     # Archivos estáticos copiados tal cual (favicon, futuras imágenes)
├── src/
│   ├── app/
│   │   ├── core/               # Infraestructura singleton
│   │   │   ├── auth/           # AuthService, AuthorizationService (permisos), TokenStorage, modelos
│   │   │   ├── config/         # API_URL
│   │   │   ├── guards/         # authGuard, eventManagerGuard, guestGuard
│   │   │   ├── http/           # Normalización y traducción de errores de la API
│   │   │   ├── interceptors/   # authInterceptor (Bearer solo hacia la API)
│   │   │   └── services/       # FlashMessageService (aviso de un solo uso entre páginas)
│   │   ├── shared/             # Reutilizable y sin lógica de negocio
│   │   │   ├── components/     # button, form-field, date-time-input, loading, empty-state, error-state, alert, pagination
│   │   │   ├── pipes/          # appDate, dateRange
│   │   │   └── utils/          # RequestState, validadores, mensajes de validación, fechas y horas (date-time)
│   │   ├── layout/
│   │   │   ├── components/     # site-header (navegación responsive y sesión), site-footer
│   │   │   └── layouts/main-layout/
│   │   ├── features/           # Una carpeta por funcionalidad, cargada de forma diferida
│   │   │   ├── events/
│   │   │   │   ├── index.ts    # API pública de la feature (EventCard, EventModel)
│   │   │   │   ├── events.routes.ts
│   │   │   │   ├── models/     # EventModel, EventPage, EventSession, reglas de estado
│   │   │   │   ├── services/   # EventsService, SessionsService, SpeakersService
│   │   │   │   ├── components/ # event-card, event-form, event-status-badge, session-list,
│   │   │   │   │               # session-form, registration-panel
│   │   │   │   └── pages/      # list, detail, create, edit
│   │   │   ├── auth/
│   │   │   │   ├── auth.routes.ts
│   │   │   │   └── pages/      # login, register
│   │   │   ├── profile/
│   │   │   │   ├── profile.routes.ts
│   │   │   │   └── pages/      # profile-page
│   │   │   ├── registrations/  # RegistrationsService (inscribirse, mis inscripciones) + index.ts
│   │   │   ├── forbidden/      # Página «Acceso denegado» + index.ts
│   │   │   └── not-found/
│   │   │       └── pages/not-found-page/
│   │   ├── app.ts              # Componente raíz: solo contiene <router-outlet />
│   │   ├── app.config.ts       # Proveedores globales (router, HttpClient, zoneless)
│   │   └── app.routes.ts       # Árbol de rutas raíz
│   ├── environments/
│   │   ├── environment.model.ts        # Interfaz común de los entornos
│   │   ├── environment.ts              # Producción (por defecto)
│   │   └── environment.development.ts  # Desarrollo (reemplazo vía fileReplacements)
│   ├── styles/
│   │   ├── _variables.scss     # Tokens: colores, tipografía, espaciado, radios, sombras, breakpoints
│   │   ├── _mixins.scss        # respond-to, container, focus-ring, visually-hidden
│   │   └── _global.scss        # Custom properties, reset moderado, tipografía base, accesibilidad
│   ├── testing/                # Utilidades de pruebas (excluidas del build de la app)
│   ├── styles.scss             # Punto de entrada de estilos globales
│   ├── index.html
│   └── main.ts
├── angular.json
├── eslint.config.js
└── package.json
```

No se mantienen carpetas vacías: `shared/directives`, `features/registrations`, etc. se crearán cuando
contengan código real.

Los nombres de archivo siguen la guía de estilo de Angular 20: `event-list-page.ts` en lugar de
`event-list-page.component.ts`, y la clase `EventListPage` en lugar de `EventListPageComponent`.

`AuthService` vive en `core/` (y no en `features/auth`) porque lo usan el interceptor, los guards y el
layout; `features/auth` solo contiene las páginas.

### Responsabilidades y reglas de dependencia

- **core/**: servicios singleton de infraestructura (`providedIn: 'root'`), tokens de configuración,
  guards e interceptores funcionales. No contiene UI ni lógica de una funcionalidad concreta.
- **shared/**: piezas visuales y utilidades **sin estado de negocio**. No se colocan servicios de datos
  aquí.
- **layout/**: estructura común de las páginas. Puede usar `core` y `shared`.
- **features/**: cada funcionalidad es autónoma. Puede depender de `core` y `shared`. Solo puede usar
  otra feature a través de su `index.ts` (API pública), nunca importando rutas internas: `profile` usa
  `EventCard` y `EventModel` desde `features/events`. Si algo pasa a ser genérico, se mueve a `shared`
  (UI) o `core` (infraestructura).

## Convenciones para añadir una funcionalidad

1. Crear la carpeta `src/app/features/<feature>/` con la organización que necesite:

   ```text
   features/events/
   ├── events.routes.ts       # Rutas de la feature (export const EVENTS_ROUTES: Routes)
   ├── pages/                 # Componentes enrutables (event-list-page/, event-detail-page/)
   ├── components/            # Componentes de presentación propios de la feature
   ├── services/              # Acceso a datos y estado (signals) de la feature
   └── models/                # Interfaces y tipos del dominio en el cliente
   ```

2. Generar componentes con el CLI (ya configurados con SCSS y `OnPush`):

   ```bash
   npx ng generate component features/events/pages/event-list-page
   ```

3. Registrar la feature en `app.routes.ts` con carga diferida, dentro del layout:

   ```ts
   {
     path: 'events',
     loadChildren: () => import('./features/events/events.routes').then((m) => m.EVENTS_ROUTES),
   },
   ```

   Las rutas deben declararse **antes** del comodín `**`. Cada ruta define su `title`
   (`'<Página> | Mis Eventos'`) para accesibilidad y SEO.

4. Los servicios HTTP inyectan `API_URL` en lugar de importar `environment`:

   ```ts
   private readonly http = inject(HttpClient);
   private readonly apiUrl = inject(API_URL);

   list() {
     return this.http.get<EventPage>(`${this.apiUrl}/events`);
   }
   ```

5. Reglas generales:
   - Componentes standalone con `ChangeDetectionStrategy.OnPush` (ESLint lo exige).
   - Estado local con `signal`/`computed`; RxJS para HTTP y flujos de eventos (`toSignal` cuando se
     necesite en la plantilla).
   - Formularios con Reactive Forms tipados (`NonNullableFormBuilder`).
   - Parámetros de ruta como `input()` gracias a `withComponentInputBinding()`.
   - Pruebas `*.spec.ts` junto al archivo probado.

## Funcionalidades y rutas

| Ruta                                                               | Acceso                       | Descripción                                                                                       |
| ------------------------------------------------------------------ | ---------------------------- | ------------------------------------------------------------------------------------------------- |
| `/` → `/events`                                                    | Público                      | Portada con buscador y catálogo paginado (`?page=`, `?search=`)                                   |
| `/events/:id`                                                      | Público                      | Detalle del evento y sus sesiones; editar/eliminar según permisos                                 |
| `/events/new` (alias `/events/create`)                             | ADMIN, ORGANIZER             | Crear evento (se guarda como `DRAFT`). Anónimo → login; sin permiso → «Acceso denegado»           |
| `/events/:id/edit`                                                 | ADMIN, ORGANIZER propietario | Editar campos y cambiar estado                                                                    |
| `/events/:id/sessions/new`, `/events/:id/sessions/:sessionId/edit` | ADMIN, ORGANIZER propietario | Crear y editar sesiones (anónimo → login; sin permiso → «Acceso denegado»)                        |
| `/auth/login`, `/auth/register`                                    | Solo anónimos                | Inicio de sesión y registro de asistentes                                                         |
| `/profile`                                                         | Autenticados (`authGuard`)   | Datos del usuario y eventos en los que está inscrito. Sin sesión → login con `returnUrl=/profile` |

### Integración con la API

Solo se usan endpoints existentes del backend (`back/README.md`):

| Endpoint                                                                  | Uso                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `GET /api/events?page&per_page&search`                                    | Catálogo. Paginación y búsqueda (por nombre) en el servidor; 9 eventos por página                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `POST /api/events/{id}/sessions`, `GET`/`PUT`/`DELETE /api/sessions/{id}` | Gestión de sesiones (`SessionsService`): crear y editar en `/events/:id/sessions/...` (el formulario valida horario dentro del evento, inicio < fin y capacidad > 0, igual que el backend); eliminar desde el detalle con confirmación (se quita de la lista sin recargarla). La sección «Sesiones del evento» es visible para todos; «Añadir sesión» (también en el estado vacío), «Editar» y «Eliminar» solo para ADMIN u ORGANIZER propietario y si el evento no está cancelado ni finalizado. A un ADMIN/ORGANIZER que no puede gestionarlas se le explica el motivo |
| `GET /api/speakers`                                                       | Catálogo de ponentes de solo lectura (`SpeakersService.listAll`, páginas de 100): selector «Ponente» del formulario y nombre del ponente en el detalle (solo se pide si alguna sesión tiene ponente)                                                                                                                                                                                                                                                                                                                                                                     |
| `GET /api/events/{id}` y `GET /api/events/{id}/sessions`                  | Detalle: dos peticiones en paralelo, cada una con su propio estado de carga y error                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `POST /api/events` / `PUT /api/events/{id}`                               | Crear / editar (no existe `PATCH`). `status` solo se envía si cambia                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `DELETE /api/events/{id}`                                                 | Borrador: se elimina (204). Publicado: se cancela (200) y la vista se actualiza con la respuesta                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`     | Registro (siempre `ATTENDEE`), JWT y usuario actual                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `POST /api/events/{id}/registrations`                                     | Inscripción desde el detalle (cuerpo vacío; el usuario sale del token). Solo eventos `PUBLISHED`. 201 → «Estás inscrito»; 409 duplicado → se trata como inscrito; 409 sin plazas o no abierto, 404 → mensaje; 401 → fin de sesión e invitación a iniciar sesión                                                                                                                                                                                                                                                                                                          |
| `GET /api/me/registrations`                                               | Perfil. Devuelve un array de eventos (`EventSchema`, el mismo `EventModel` del catálogo) ordenado por fecha de inicio, incluidos los cancelados o finalizados. No incluye datos propios de la inscripción (fecha ni estado), por lo que la tarjeta muestra el estado del evento                                                                                                                                                                                                                                                                                          |

Los modelos de `features/events/models` y `core/auth/auth.models.ts` reflejan los esquemas marshmallow
del backend. Los errores `{ message, errors: { json: { campo: [...] } } }` se normalizan en
`core/http/api-error.ts`: los errores por campo (422) se muestran en el campo correspondiente y los
mensajes conocidos (correo duplicado, credenciales, transiciones de estado, capacidad...) se traducen.

No hay caché de datos: cada página consulta la API al entrar, de modo que tras crear, editar o eliminar
no quedan datos obsoletos. El listado y el detalle se recargan además cuando cambia el usuario, porque
la visibilidad de los eventos depende de él.

### Limitaciones del backend detectadas

- **Ponentes**: las sesiones solo exponen `speaker_id` y no existe `GET /api/speakers` (está en el
  roadmap del backend). La interfaz no muestra datos de ponentes en lugar de inventarlos.
- **Búsqueda**: solo por nombre del evento (`search`); no hay búsqueda por ubicación ni por fecha.
- **Imágenes, precio y plazas libres**: el modelo de evento no tiene imagen, precio ni número de
  inscritos, así que las tarjetas muestran solo datos reales (la franja de color es decorativa).
- **Gestión de sesiones** (crear, editar, eliminar): existe en la API, pero no forma parte de esta fase.

## Autenticación, sesión y permisos

- `AuthService` es la única fuente del estado de sesión (signals `user` e `isAuthenticated`). El usuario
  y su rol se obtienen siempre de `GET /api/auth/me`; el JWT no se decodifica en el navegador.
- **Almacenamiento del token**: el backend solo acepta `Authorization: Bearer` (no emite cookies), así
  que el token tiene que ser legible desde JavaScript. Se guarda en `sessionStorage` junto con su
  `expires_at`:
  - Sobrevive a recargas de la pestaña, se borra al cerrarla y no se comparte entre pestañas, lo que
    acota la exposición frente a `localStorage`.
  - Como cualquier almacenamiento accesible por JavaScript, es vulnerable a XSS: la app no inserta HTML
    no confiable (Angular escapa las interpolaciones). La alternativa más segura, una cookie
    `HttpOnly` + `SameSite`, requeriría cambios en el backend.
  - Los tokens caducados se descartan y la sesión se cierra automáticamente al expirar.
- Al arrancar, `provideAppInitializer` restaura la sesión (`/auth/me`) antes de la primera navegación.
- **Interceptor** (`core/interceptors/auth.interceptor.ts`): añade el token solo a URLs que empiezan por
  `API_URL` (nunca a otros dominios ni a login o registro).
  - **401** con token: la sesión ya no es válida y se cierra. Como el backend rechaza tokens inválidos
    incluso en endpoints públicos, los `GET` se reintentan una vez sin token; las mutaciones devuelven
    el error a la página. No hay redirecciones automáticas, así que no pueden producirse bucles.
  - **403**: no cierra la sesión; la página indica que no hay permiso.
- **Permisos** centralizados en `AuthorizationService`:
  - `canCreateEvents`: ADMIN y ORGANIZER. ATTENDEE y los anónimos no ven el botón «Crear evento».
  - `canManageEvent(ownerId)`: ADMIN gestiona cualquier evento; ORGANIZER solo los que creó.
  - Las reglas de estado (`isEventEditable`, `removalAction`) están en `events/models`: los eventos
    cancelados o finalizados no muestran acciones.
- **Autenticación antes que autorización** en `/events/new` y `/events/:id/edit`
  (`managerPage()` en `events.routes.ts`):
  1. Anónimo → `/auth/login?returnUrl=<ruta pedida>` y, tras iniciar sesión, vuelta a esa ruta.
  2. Autenticado sin permiso (ATTENDEE) → página «Acceso denegado» en la propia URL pedida, sin
     cerrar la sesión ni redirigir al login o al catálogo.
  3. ADMIN u ORGANIZER → formulario.

  La ruta del formulario solo coincide si `canManageEventsMatch` lo permite; si no, el router usa una
  ruta gemela con la misma URL protegida por `authGuard` que muestra el acceso denegado.
  `eventManagerGuard` vuelve a comprobar sesión y rol en la ruta del formulario. La propiedad del
  evento se comprueba al cargarlo en la página de edición. `guestGuard` aparta a los usuarios
  autenticados de login y registro. `returnUrl` solo admite rutas internas.

- **Rutas de eventos**: las estáticas (`new`) se declaran antes que las de id, y `:id` / `:id/edit`
  solo aceptan ids numéricos (`eventIdMatcher`), así que un segmento como `create` o `abc` nunca se
  interpreta como id ni provoca `GET /events/NaN`: `/events/create` es un alias de `/events/new` y el
  resto muestra la página 404.
- **HTTP 401 frente a 403**: un 401 termina la sesión (y, en una ruta protegida, lleva al login); un
  403 la conserva y la página muestra que no hay permiso.
- El backend sigue siendo la autoridad: vuelve a comprobar el rol (desde su base de datos) y la
  propiedad en cada petición; la interfaz solo evita ofrecer acciones que fallarían.

## Gestión del estado

No hay un store global (NgRx u otro): el estado compartido es poco y vive en servicios `root` con
**signals**; el estado de cada pantalla se deriva de la URL y de la API.

| Estado                                          | Dónde vive                                                                                                            | Quién lo usa                        |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Usuario, sesión (`user`, `isAuthenticated`)     | `AuthService` (signals de solo lectura)                                                                               | Cabecera, guards, permisos, páginas |
| Token y su caducidad                            | `TokenStorage` (`sessionStorage`), solo a través de `AuthService`                                                     | Interceptor                         |
| Permisos (`canCreateEvents`, `canManageEvent`)  | `AuthorizationService` (`computed` sobre el usuario)                                                                  | Cabecera, listado, detalle, edición |
| Fin de sesión (`logout`, `expired`, `rejected`) | `AuthService.sessionEnded$` (una emisión por sesión)                                                                  | `SessionExpiryRedirect`             |
| Mensaje entre páginas                           | `FlashMessageService` (un solo uso)                                                                                   | Páginas de destino                  |
| Listado, detalle, sesiones, perfil              | Cada página: `toSignal(toObservable(clave).pipe(switchMap(...)))` → `RequestState<T>` (`loading`, `success`, `error`) | La propia página                    |

Reglas que mantienen la interfaz coherente:

- **La clave de cada carga incluye al usuario** (además de la página, la búsqueda o el id). Al iniciar o
  cerrar sesión, el listado, el detalle y el perfil vuelven a pedir los datos con la nueva identidad y
  muestran `loading` mientras tanto, de modo que nunca se ven datos del usuario anterior. El perfil no
  consulta la API sin sesión.
- **`switchMap` cancela la petición anterior** si la clave cambia antes de que responda (cambios
  rápidos de página o de búsqueda), así que una respuesta antigua no puede pisar a la nueva.
- **Sin caché**: cada página consulta al entrar, por lo que tras crear, editar o eliminar no quedan
  datos obsoletos. El estado transitorio del detalle (aviso, confirmación de eliminación) se reinicia
  al cambiar de evento o de usuario (`linkedSignal`).
- **Fin de sesión**:
  - _Logout_: `AuthService` borra token, usuario y mensajes pendientes; la cabecera se actualiza al
    instante y navega al catálogo.
  - _Token caducado o 401_: además, si la ruta activa está protegida (`authGuard`,
    `eventManagerGuard`), `SessionExpiryRedirect` lleva una sola vez al login con `returnUrl` y un aviso.
    El fin de sesión es idempotente: varios 401 simultáneos producen una única redirección. El
    interceptor reintenta una vez sin token solo los `GET` y la página de login no hace peticiones
    autenticadas, así que no hay bucles.

## Configuración de la URL de la API

La URL se define con el mecanismo oficial de entornos de Angular CLI:

| Archivo                                       | Se usa en                        | `apiUrl`                    |
| --------------------------------------------- | -------------------------------- | --------------------------- |
| `src/environments/environment.development.ts` | `npm start`, `npm run build:dev` | `http://localhost:5000/api` |
| `src/environments/environment.ts`             | `npm run build` (producción)     | `/api` (mismo origen)       |

`apiUrl` incluye el prefijo `/api` que usan todas las rutas del backend. En producción se usa una ruta
relativa, pensada para servir el frontend y la API bajo el mismo dominio mediante un proxy inverso; si
la API se publica en otro dominio, basta con cambiar el valor en `environment.ts`.

El valor se expone a la aplicación mediante el token `API_URL` (`core/config/api-url.token.ts`), que las
pruebas pueden sobrescribir con `{ provide: API_URL, useValue: '...' }`.

### Seguridad

- **Todo lo que está en `environment*.ts` acaba en el bundle de JavaScript y es público.** Cualquier
  usuario puede leerlo desde el navegador. Nunca se deben incluir secretos, claves privadas ni tokens.
- Angular no lee archivos `.env` en tiempo de ejecución: la aplicación es código estático que se ejecuta
  en el navegador. Por eso este proyecto no tiene `.env.example`; la configuración se fija en tiempo de
  compilación con los archivos de entorno.
- La minificación no es una medida de seguridad ni oculta información.
- CORS se configura en el backend (`CORS_ORIGINS`), no en el frontend.

## Rendimiento

- **Carga diferida**: cada feature y cada página se cargan bajo demanda (`loadChildren` /
  `loadComponent`). El componente raíz no importa ninguna funcionalidad. El build muestra los
  _lazy chunks_ generados.
- **Build de producción** (configuración por defecto de `ng build`): optimización de scripts y estilos
  (minificación), tree-shaking, eliminación de código muerto, inlining de CSS crítico, hashing de
  nombres para caché de larga duración (`outputHashing: all`), sin source maps y con presupuestos de
  tamaño (`budgets`) que fallan el build si se superan.
- **Zoneless + OnPush**: sin `zone.js` en el bundle; la detección de cambios se basa en signals.
- **HTTP**: `provideHttpClient(withFetch(), withInterceptors([authInterceptor]))`. Las lecturas usan
  `switchMap`, de modo que un cambio de página o de búsqueda cancela la petición anterior. Las
  suscripciones manuales usan `takeUntilDestroyed`; el resto se convierte a signals con `toSignal`.
- **Sin caché de datos** por ahora (ver [Integración con la API](#integración-con-la-api)).

### Imágenes

- Formatos modernos (**AVIF** o **WebP**) con dimensiones ajustadas a su contexto de uso.
- **Portadas de eventos (Cloudinary).** Las URLs se construyen solo en
  `shared/utils/cloudinary-image.ts` (en plantillas, pipe `responsiveImage`): `f_auto` (AVIF/WebP
  cuando el navegador los admite, sin forzar WebP), `q_auto` y `c_fill,g_auto` con proporción fija
  por uso, generadas bajo demanda por el CDN de Cloudinary:

  | Uso               | Proporción | Variantes (`srcset`)                    |
  | ----------------- | ---------- | --------------------------------------- |
  | Tarjeta (`card`)  | 16:10      | 400×250 (móvil), 800×500 (pantallas 2x) |
  | Portada (`cover`) | 16:9       | 400×225, 800×450, 1200×675, 1920×1080   |

  Los anchos siguen los dispositivos de referencia (móvil 400, tablet 800, escritorio 1200, alta
  resolución 1920); la altura sigue la proporción real de cada lugar para que el diseño no salte.
  Las tarjetas usan `loading="lazy"` y la portada del detalle `fetchpriority="high"`. No se usa
  `NgOptimizedImage`: su _loader_ de Cloudinary solo varía el ancho (sin recorte con proporción fija)
  y obligaría a configurar el `cloud_name` en el frontend; con `secure_url` basta.

- **Subida.** `EventImagesService` pide la firma al backend (solo nombre, tipo y tamaño), envía el
  archivo directamente a Cloudinary y confirma el `public_id`; el interceptor nunca añade el JWT a
  Cloudinary. El formulario valida antes tipo (JPG, PNG, WebP) y tamaño (5 MB), muestra una vista
  previa local (`blob:`) y el estado de cada etapa, y bloquea el envío mientras dura. La imagen se
  sube después de guardar el evento (al crear hace falta su id); si falla, el evento se conserva y
  se informa del problema. Salir de la página cancela la subida en curso. Con `withFetch()` Angular
  no informa del progreso de subida, así que el estado no muestra porcentaje.
- La CSP de Nginx permite `img-src https://res.cloudinary.com blob:` y
  `connect-src https://api.cloudinary.com`.
- Iconos y logotipos simples, preferiblemente en SVG.
- Estáticos del proyecto en `public/`; no subir imágenes grandes al repositorio.

## Fundamentos de UI

### Tokens de diseño

Los tokens se definen en `src/styles/_variables.scss` y se publican como _custom properties_ en
`:root`. Los componentes los consumen con `var(--token)`:

| Grupo      | Ejemplos                                                                                                       |
| ---------- | -------------------------------------------------------------------------------------------------------------- |
| Colores    | `--color-primary` (violeta), `--color-secondary` (azul), `--gradient-brand`, `--color-text`, `--color-surface` |
| Estados    | `--color-success`, `--color-warning`, `--color-danger`, `--color-info` (+ variantes `-subtle`)                 |
| Tipografía | `--font-size-sm` … `--font-size-4xl`, `--font-weight-*`, `--line-height-*`                                     |
| Espaciado  | `--space-1` (4px) … `--space-8` (64px)                                                                         |
| Bordes     | `--border-width`, `--radius-sm/md/lg/xl/full`, `--shadow-sm/md/lg`                                             |

Los breakpoints (`sm` 576px, `md` 768px, `lg` 1024px, `xl` 1280px) son valores Sass porque las media
queries no admiten custom properties. En los componentes:

```scss
@use 'mixins' as mx;

.grid {
  display: grid;

  @include mx.respond-to(md) {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

`src/styles` está registrado en `stylePreprocessorOptions.includePaths`, así que no hacen falta rutas
relativas. El diseño es _mobile first_.

### Accesibilidad

- Enlace "Saltar al contenido principal", landmarks semánticos (`header`, `nav`, `main`, `footer`) y
  `lang="es"`.
- Foco visible con `:focus-visible` (mixin `focus-ring`); nunca eliminar el `outline` sin alternativa.
- Colores de texto con contraste WCAG AA.
- `prefers-reduced-motion` respetado globalmente.
- Título de documento por ruta y reglas de accesibilidad de `angular-eslint` en las plantillas.

### Convenciones para estados de interfaz

Implementadas en `shared/components/` (`app-loading`, `app-empty-state`, `app-error-state`,
`app-alert`) y en `shared/utils/request-state.ts` (`RequestState<T>`: `loading | success | error`):

| Estado       | Pauta                                                                                                                                          |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Carga        | Contenedor con `aria-busy="true"`; texto o _skeleton_ con `role="status"`. No bloquear toda la página.                                         |
| Vacío        | Mensaje claro con la causa y, si aplica, una acción para salir del estado vacío.                                                               |
| Error        | `role="alert"`, colores `--color-danger` / `--color-danger-subtle`, mensaje comprensible y opción de reintentar.                               |
| Confirmación | `role="status"` (aviso no intrusivo) con `--color-success` / `--color-success-subtle`. Las acciones destructivas piden confirmación explícita. |

Las plantillas usan el control de flujo nativo (`@if`, `@for`, `@defer`) para representar estos
estados.

### Componentes compartidos

| Componente                                                       | Uso                                                                                                                                                        |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `button[appButton]`, `a[appButton]`                              | Variantes `primary/secondary/ghost/danger/inverse`, tamaño y `loading` (spinner + `aria-busy`). Conserva la semántica nativa                               |
| `app-form-field`                                                 | Etiqueta, control (`text`, `email`, `password`, `number`, `datetime`, `textarea`, `select`), ayuda y error enlazados con `aria-describedby`/`aria-invalid` |
| `app-pagination`                                                 | Paginación del servidor: emite la página pedida; el estado vive en la URL                                                                                  |
| `app-loading`, `app-empty-state`, `app-error-state`, `app-alert` | Estados de interfaz                                                                                                                                        |

### Fechas y horas

Toda la lógica temporal vive en `shared/utils/date-time.ts` (sin dependencias, sobre `Intl`):

- Se muestran siempre en la zona de Colombia (`America/Bogota`) y con la configuración regional
  `es-CO`, sea cual sea la zona del dispositivo. No se suman ni restan horas a mano: el desfase sale
  de la base de datos de zonas horarias del navegador.
- Formatos: fecha `dd/MM/yyyy` (`10/10/2026`), hora `h:mm a` (`2:45 PM`) y fecha y hora
  `dd/MM/yyyy, h:mm a`. En plantillas: `value | appDate: 'date' | 'time' | 'datetime'` y
  `start | dateRange: end`. No se usa el pipe `date` de Angular, que depende de la zona del dispositivo.
- La API intercambia instantes ISO 8601 (el backend responde en UTC). Los formularios editan la hora
  de Colombia (`toColombiaInput` / `fromColombiaInput`) y envían de nuevo un instante UTC.
- Las fechas civiles sin hora (`2026-10-10`) no se convierten de zona, para que no cambien de día.
- `app-form-field type="datetime"` usa `app-date-time-input`: fecha nativa más hora, minutos y AM/PM
  en selectores, porque `datetime-local` y `time` siguen la configuración del navegador y pueden
  mostrar 24 horas. El valor del control sigue siendo `yyyy-MM-ddTHH:mm`.

## Pruebas

`npm run test:ci` ejecuta las pruebas en Chrome headless. Usan el `HttpClient` real con el interceptor
contra `HttpTestingController` y el router real (`RouterTestingHarness`); `src/testing/test-helpers.ts`
inicia sesión a través del `AuthService` real respondiendo a `/auth/login` y `/auth/me`.

Cubren: listado (carga, tarjetas, vacío, error y reintento, paginación y búsqueda en la URL), detalle
(sesiones, 404, acciones según rol y propiedad, eliminar y cancelar), formulario de eventos (validaciones,
payload, errores del servidor, doble envío), edición (propiedad, `PUT`, conflictos 409), login,
registro, `AuthService`, `AuthorizationService`, interceptor (dominios, 401, 403), guards, cabecera
(botón «Crear evento» por rol) y paginación.

## Pendiente para próximas fases

- Gestión de ponentes (alta, edición, baja): fuera del alcance; las sesiones asignan ponentes ya
  existentes mediante `GET /api/speakers`.
- El backend no informa de plazas libres ni de la fecha de inscripción en `GET /me/registrations`; el
  detalle consulta esa lista para saber si el usuario ya está inscrito.
- Filtro por estado del catálogo para organizadores (`?status=` ya existe en la API).
- Estrategia de caché HTTP si el volumen de datos lo justifica.
