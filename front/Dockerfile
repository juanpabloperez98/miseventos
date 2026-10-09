# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Build stage: compile the Angular application for production.
# ---------------------------------------------------------------------------
FROM node:22.17-alpine AS build

WORKDIR /app

# Dependency layer: only invalidated when package.json or package-lock.json change.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
# Production configuration: apiUrl is the relative path "/api" (src/environments/environment.ts),
# served by the Nginx reverse proxy below.
RUN npm run build

# ---------------------------------------------------------------------------
# Runtime stage: static files served by Nginx. No Node.js, sources or node_modules.
# ---------------------------------------------------------------------------
FROM nginx:1.28-alpine AS runtime

# Upstream that receives /api/ requests. Resolved inside the Docker network at request time.
ENV BACKEND_UPSTREAM=http://backend:5000
# HTTPS behind an external TLS proxy (see the root README): redirect requests the proxy reports as
# plain HTTP (1/0) and the Strict-Transport-Security value to send over HTTPS (empty = disabled).
ENV HTTPS_REDIRECT=0 \
    HSTS_HEADER=""

# The official image renders /etc/nginx/templates/*.template with envsubst on start-up.
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
# Only the compiled app is served: drop the image's default pages first.
RUN rm -rf /usr/share/nginx/html/*
# angular.json → outputPath "dist/mis-eventos"; the application builder writes the browser bundle
# to its "browser" subfolder.
COPY --from=build /app/dist/mis-eventos/browser /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/index.html || exit 1
