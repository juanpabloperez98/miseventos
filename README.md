# Mis Eventos

Plataforma de gestión de eventos: API REST en Flask ([`back/`](back/README.md)), cliente web en
Angular ([`front/`](front/README.md)) y PostgreSQL, orquestados con Docker Compose.

```text
                 navegador
                    │  http://localhost:4200
                    ▼
        ┌──────────────────────────┐
        │ frontend (Nginx)         │  Angular compilado + proxy /api/ → backend:5000
        └────────────┬─────────────┘
                     │  red Docker "miseventos"
        ┌────────────▼─────────────┐
        │ backend (Flask)          │  dev: Flask --debug · prod: Gunicorn
        └────────────┬─────────────┘
        ┌────────────▼─────────────┐
        │ postgres:17-alpine       │  volumen nombrado postgres_data
        └──────────────────────────┘
```

| Archivo                                                 | Contenido                                                                    |
| ------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `docker-compose.yml`                                    | Stack completo en modo **desarrollo** (configuración por defecto)            |
| `docker-compose.prod.yml`                               | **Producción**: solo backend (Gunicorn) + PostgreSQL                         |
| `back/Dockerfile`, `back/scripts/start.sh`              | Imagen del backend: migraciones → seeder (solo desarrollo) → servidor        |
| `front/Dockerfile`, `front/nginx/default.conf.template` | Build de Angular con Node y servido con Nginx (fallback SPA y proxy `/api/`) |

## Requisitos previos

- Docker Engine con Docker Compose v2.24 o superior (los overrides usan `!reset`).
- Solo para desarrollo del frontend fuera de Docker: Node.js 22 (ver [`front/README.md`](front/README.md)).

## Configuración inicial

```bash
cp .env.example .env              # Credenciales de PostgreSQL y puertos publicados
cp back/.env.example back/.env    # Configuración del backend (JWT, CORS, seeders...)
```

Edita ambos archivos y sustituye los valores de ejemplo (contraseñas, `JWT_SECRET_KEY` de al menos 32
caracteres, contraseñas `SEED_*`). Los `.env` están excluidos de Git y de las imágenes Docker
(`.gitignore` y `back/.dockerignore`).

| Variable (`.env` raíz)                              | Uso                                                                                   | Por defecto      |
| --------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------------- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Credenciales de PostgreSQL; Compose construye con ellas el `DATABASE_URL` del backend | — (obligatorias) |
| `POSTGRES_HOST_PORT`                                | Puerto de PostgreSQL en el host (solo desarrollo)                                     | `5432`           |
| `BACKEND_HOST_PORT`                                 | Puerto de la API en el host (solo desarrollo)                                         | `5000`           |
| `FRONTEND_HOST_PORT`                                | Puerto del frontend Nginx en el host                                                  | `4200`           |

Las variables del backend (`FLASK_ENV`, `JWT_SECRET_KEY`, `JWT_EXPIRATION_MINUTES`, `CORS_ORIGINS`,
`LOG_LEVEL`, `SEED_*`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`) están descritas en
`back/.env.example` y en [`back/README.md`](back/README.md#environment-variables).

**El frontend no tiene secretos.** Su única configuración es `apiUrl`, que se fija al compilar
(`front/src/environments/`) y es pública: en producción vale `/api` (ruta relativa hacia el proxy de
Nginx). Cambiar variables del contenedor no modifica el bundle ya compilado; la única variable del
contenedor del frontend es `BACKEND_UPSTREAM`, el destino del proxy dentro de la red Docker
(`http://backend:5000` por defecto).

## Levantar todo el stack

### Desarrollo (por defecto)

```bash
docker compose up -d --build
docker compose ps        # los tres servicios deben aparecer como (healthy)
```

| Servicio                                         | URL                                                                 |
| ------------------------------------------------ | ------------------------------------------------------------------- |
| Frontend (Nginx, build de producción de Angular) | <http://localhost:4200>                                             |
| API directa                                      | <http://localhost:5000/api>                                         |
| Salud del backend                                | <http://localhost:5000/health>                                      |
| Swagger UI / OpenAPI                             | <http://localhost:5000/docs> · <http://localhost:5000/openapi.json> |
| PostgreSQL                                       | `localhost:5432`                                                    |

En desarrollo el backend monta `./back` y usa el servidor de Flask con recarga; al arrancar aplica las
migraciones y ejecuta el seeder idempotente (no duplica datos). El frontend del contenedor es
siempre el build optimizado servido por Nginx; para recarga en caliente usa `npm start` (siguiente
sección).

### Producción

`docker-compose.prod.yml` es independiente (**no** se aplica encima de `docker-compose.yml`) y solo
ejecuta el backend con Gunicorn y PostgreSQL. El frontend no forma parte de él: su build estático lo
sirve un Nginx instalado en el servidor, que reenvía `/api/` a `127.0.0.1:5001`
(configuración del servidor fuera de este repositorio).

Configuración en el servidor (archivos ignorados por Git):

| Archivo                                      | Variables                                                                                                                                                          |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `.env` (raíz, plantilla `.env.example`)      | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (obligatorias: Compose falla si faltan); `BACKEND_ENV_FILE` opcional. El puerto es fijo (`127.0.0.1:5001`) |
| `back/.env` (o el de `BACKEND_ENV_FILE`)     | `JWT_SECRET_KEY` (obligatoria), `CORS_ORIGINS`, `JWT_EXPIRATION_MINUTES`, `LOG_LEVEL`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `CLOUDINARY_*`, `EVENT_IMAGE_MAX_BYTES` |

- Sustituye todos los valores de ejemplo (`change-me`, `replace-with-...`). `POSTGRES_PASSWORD` se
  inserta sin codificar en `DATABASE_URL`: usa solo letras, dígitos, `-` y `_`
  (`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`).
- `docker-compose.prod.yml` fija `FLASK_ENV=production`, `DATABASE_URL` y `SEED_*_ENABLED=false`, por
  encima de lo que diga `back/.env`.
- Si el frontend se sirve en el mismo dominio que `/api/`, deja `CORS_ORIGINS` vacío.

```bash
docker compose -f docker-compose.prod.yml config --quiet     # valida archivo y variables
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps                 # ambos servicios (healthy)
curl -fsS http://127.0.0.1:5001/health
```

**Migraciones.** En cada arranque, `back/scripts/start.sh` valida la configuración, ejecuta
`alembic upgrade head` (solo hacia delante) y después arranca Gunicorn; en el primer despliegue crea
el esquema. Para una actualización que incluya migraciones, haz antes un backup de la base de datos
y aplícalas de forma explícita antes de sustituir el backend:

```bash
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.prod.yml up -d backend
docker compose -f docker-compose.prod.yml exec backend alembic current
```

Si una migración falla, PostgreSQL revierte la transacción y el backend en marcha no cambia; si
fallara durante un arranque, el contenedor se reiniciaría en bucle hasta corregirla (ver
`docker compose -f docker-compose.prod.yml logs backend`).

Diferencias respecto a desarrollo:

|                    | Desarrollo                                                  | Producción                                                                                         |
| ------------------ | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Backend            | Flask `--debug`, código montado, dependencias de desarrollo | Gunicorn, imagen `miseventos-backend:prod` sin dependencias de desarrollo ni código montado        |
| `FLASK_ENV`        | El de `back/.env`                                           | `production` (forzado por `docker-compose.prod.yml`)                                               |
| Seeder             | Se ejecuta en cada arranque (idempotente)                   | Prohibido: `SEED_*_ENABLED` forzados a `false` y el backend no arranca si alguno vale `true`       |
| `JWT_SECRET_KEY`   | Mínimo 32 caracteres                                        | Además: sin marcadores de ejemplo y con al menos 16 caracteres distintos, o el backend no arranca  |
| Puertos publicados | 4200, 5000, 5432                                            | Solo 5000 en `127.0.0.1` (para el Nginx del host); PostgreSQL solo es accesible en una red interna |

Ver [Seguridad en producción](#seguridad-en-producción) antes de un despliegue real.

## Seguridad en producción

### Configuración del backend y `JWT_SECRET_KEY`

Usa un archivo de configuración propio del servidor, fuera del repositorio, e indícalo con
`BACKEND_ENV_FILE` en el `.env` raíz (por defecto `./back/.env`):

```bash
# Genera una clave distinta por entorno y guárdala solo en ese archivo o en tu gestor de secretos.
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

- El backend valida la configuración **antes de ejecutar las migraciones** (`back/scripts/start.sh`).
  En producción se niega a arrancar si `JWT_SECRET_KEY` falta, tiene menos de 32 caracteres, contiene
  un valor de ejemplo (`replace-with`, `change-me`) o tiene menos de 16 caracteres distintos. Los
  mensajes de error nunca muestran la clave.
- La clave no se genera automáticamente: debe ser estable, porque cambiarla invalida todos los
  tokens emitidos.
- En desarrollo basta con los 32 caracteres; el valor de `back/.env.example` sirve para probar.
- Cambia también `POSTGRES_PASSWORD` y no publiques nunca los `.env` (están en `.gitignore` y en los
  `.dockerignore`).

### Seeders

- `docker-compose.prod.yml` fuerza `SEED_ADMIN_ENABLED`, `SEED_ORGANIZER_ENABLED`,
  `SEED_ATTENDEE_ENABLED` y `SEED_DEMO_DATA_ENABLED` a `false`.
- Si con `FLASK_ENV=production` alguno de ellos vale `true`, el backend (y cualquier comando `flask`)
  falla al arrancar con `Seeding must be disabled in production`, sin tocar la base de datos.
- `start.sh` no ejecuta el seeder en producción, y el comando `seed-initial-data` se niega igualmente
  si se lanza a mano.

### HTTPS

En producción, HTTPS lo termina el Nginx del servidor, que se configura fuera de este repositorio.

Lo que sigue aplica al frontend **dockerizado** (`front/Dockerfile`), que ahora solo forma parte del
stack de desarrollo, si se publica detrás de un **terminador TLS externo** (proxy inverso o
balanceador del proveedor) delante del puerto del frontend.

1. El proxy externo termina TLS, reenvía a `http://<servidor>:${FRONTEND_HOST_PORT}` y fija la
   cabecera `X-Forwarded-Proto` (sobrescribiendo la del cliente).
2. Nginx conserva ese `X-Forwarded-Proto` al reenviar `/api/` al backend.
3. Variables del contenedor del frontend (`ENV` de `front/Dockerfile`, sobrescribibles en el bloque
   `environment` del servicio `frontend`):

   | Variable           | Efecto                                                                                                                                                                                                    | Por defecto         |
   | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
   | `HTTPS_REDIRECT=1` | Redirige con `301` a `https://` las peticiones que el proxy marca como `X-Forwarded-Proto: http`. Las peticiones sin esa cabecera (health checks, tráfico interno) no se redirigen, así que no hay bucles | `0`                 |
   | `HSTS_HEADER`      | Valor de `Strict-Transport-Security`, enviado solo en respuestas servidas por HTTPS                                                                                                                       | vacío (desactivado) |

   Activa `HTTPS_REDIRECT` solo detrás de un proxy que controle `X-Forwarded-Proto`. Empieza con
   `HSTS_HEADER=max-age=300` y aumenta el valor (y `includeSubDomains`) solo cuando HTTPS funcione en
   todos los hosts afectados.

4. El backend no genera URLs absolutas, redirecciones ni cookies, por lo que no necesita conocer el
   esquema original (no se usa `ProxyFix`).

Pendiente para un despliegue real: dominio, certificado y el proxy o balanceador con TLS.

### Cabeceras del frontend

Nginx envía `Content-Security-Policy` (`script-src 'self'`, `connect-src 'self'`,
`frame-ancestors 'none'`; `style-src` permite estilos inline porque Angular inserta los estilos de
los componentes), `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` y
`Permissions-Policy` (`front/nginx/security-headers.conf`). El build de producción no usa el inlining
de CSS crítico de Angular, que requiere un manejador `onload` inline incompatible con este CSP.

## Frontend en modo desarrollo (recarga en caliente)

Levanta solo la base de datos y la API, y ejecuta Angular en el host:

```bash
docker compose up -d postgres backend
cd front
npm install
npm start               # http://localhost:4200 → llama a http://localhost:5000/api (CORS_ORIGINS)
```

`npm start` usa el puerto 4200, el mismo que el contenedor `frontend`: si este está en marcha,
detenlo con `docker compose stop frontend` o cambia `FRONTEND_HOST_PORT` en `.env`.

Para levantar **solo el frontend dockerizado**: `docker compose up -d --build frontend`. Nginx sirve la
aplicación aunque el backend no esté disponible; las llamadas a `/api/` devolverán `502` hasta que lo
esté y la interfaz mostrará su estado de error con opción de reintentar.

## Pruebas

```bash
# Backend (dentro del contenedor de desarrollo). Las pruebas de integración usan TEST_DATABASE_URL
# (base <POSTGRES_DB>_test, creada automáticamente), nunca la base de desarrollo.
docker compose exec backend pytest                         # unitarias + integración
docker compose exec backend pytest tests/unit              # solo unitarias
docker compose exec backend pytest tests/integration       # base de datos, HTTP y CLI
docker compose exec backend ruff check . && docker compose exec backend ruff format --check .
docker compose exec backend mypy
docker compose exec backend alembic check                  # modelos y migraciones coinciden

# Frontend (en el host)
cd front
npm run lint
npm run test:ci
npm run build
```

## Operación

```bash
docker compose ps                         # estado y salud de los contenedores
docker compose logs -f                    # logs de todos los servicios
docker compose logs -f backend            # logs de un servicio
docker inspect --format '{{json .State.Health}}' miseventos-backend-1   # detalle del health check

docker compose up -d --build              # reconstruir imágenes y recrear lo que haya cambiado
docker compose build --no-cache frontend  # reconstruir una imagen desde cero
docker compose restart backend            # reiniciar un servicio

docker compose stop                       # detener sin eliminar contenedores
docker compose down                       # eliminar contenedores y red; los datos se conservan
```

Para el stack de producción, usa `docker compose -f docker-compose.prod.yml` en cada comando; su
volumen es `miseventos-prod_postgres_data`.

Los datos de PostgreSQL viven en el volumen nombrado `miseventos_postgres_data` y sobreviven a
`stop`, `down` y a la recreación de contenedores. **`docker compose down -v` borra el volumen y todos
los datos**; úsalo solo si quieres empezar de cero.

### Health checks

| Servicio   | Comprobación                                                              |
| ---------- | ------------------------------------------------------------------------- |
| `postgres` | `pg_isready` (definido en `docker-compose.yml`)                           |
| `backend`  | `GET /health` desde dentro del contenedor (definido en `back/Dockerfile`) |
| `frontend` | Nginx sirve `index.html` (definido en `front/Dockerfile`)                 |

El backend espera a que PostgreSQL esté `healthy` antes de arrancar (`depends_on`). Eso solo ordena el
arranque: si la base de datos se reinicia después, el backend sigue en marcha y recupera las
conexiones en las siguientes peticiones. El frontend no depende de ningún servicio. Todos usan
`restart: unless-stopped`.

## Proxy `/api/` de Nginx

- El navegador siempre llama a rutas relativas (`/api/...`), por lo que no necesita CORS ni conocer el
  nombre `backend`, que solo existe dentro de la red Docker.
- Nginx reenvía la URI sin modificarla (las rutas del backend ya empiezan por `/api`), junto con el
  método, el cuerpo, la cabecera `Authorization` y las cabeceras `X-Forwarded-*`.
- El nombre del backend se resuelve en cada petición con el DNS interno de Docker, de modo que Nginx
  arranca aunque el backend no esté listo y sigue funcionando si el contenedor del backend se recrea.
- Rutas de Angular (`/events/2`, `/auth/login`...): `try_files` devuelve `index.html`, así que pueden
  abrirse o recargarse directamente. Los recursos con hash se sirven con caché de un año e
  `index.html` sin caché.
