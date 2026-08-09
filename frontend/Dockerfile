FROM node:22-alpine AS base
WORKDIR /app
COPY package*.json ./

# Local development target (unchanged from before this file had stages):
# npm install (not ci) matches the previous single-stage behavior; source is
# overlaid by docker-compose.yml's bind mount. docker-compose.yml pins
# `target: dev` explicitly - without that pin, a multi-stage Dockerfile with
# no --target defaults to building the *last* stage (production), which
# would silently break local dev.
FROM base AS dev
RUN npm install
COPY . .
CMD ["npm", "run", "dev"]

# Builder stage: production only needs the compiled static output, not the
# Node toolchain that produced it. npm ci (not install) for a reproducible,
# lockfile-exact build. Vite inlines VITE_* variables into the compiled
# bundle at build time (not read at container runtime), so the API base URL
# has to be supplied as a build ARG rather than a docker-compose
# `environment:` entry. The default is a same-origin relative path so the
# built bundle never depends on any particular hostname/port - the reverse
# proxy is expected to route /api/* to the backend on the same origin.
FROM base AS build
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm ci
COPY . .
RUN npm run build

# Production target: static files only, served by a minimal non-root web
# server - no Node/Vite process at runtime. nginxinc/nginx-unprivileged is
# nginx's own maintained variant that already listens on 8080 (not the
# privileged port 80) and runs as a non-root user out of the box, so this
# doesn't need to hand-roll listen-port/permission changes on top of the
# stock nginx image. The custom server block preserves React Router deep
# links by falling back to index.html when a static asset is not found.
FROM nginxinc/nginx-unprivileged:stable-alpine AS production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
