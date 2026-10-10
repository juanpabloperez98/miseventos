# syntax=docker/dockerfile:1

FROM node:22.17-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

ARG ANGULAR_CONFIGURATION=production

COPY . .
RUN npm run build -- --configuration "${ANGULAR_CONFIGURATION}"

FROM nginx:1.28-alpine AS runtime

# Origin of the apiUrl compiled into the bundle; allowed by the CSP connect-src.
ARG API_ORIGIN=https://tusdatosapi.srbucadevs.store

ENV API_ORIGIN=${API_ORIGIN}
ENV BACKEND_UPSTREAM=http://backend:5000
ENV HTTPS_REDIRECT=0 \
    HSTS_HEADER=""

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /app/dist/mis-eventos/browser /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/index.html || exit 1
