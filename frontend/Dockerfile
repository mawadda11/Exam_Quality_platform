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
# lockfile-exact build.
FROM base AS build
RUN npm ci
COPY . .
RUN npm run build

# Production target: static files only, served by a minimal non-root web
# server - no Node/Vite process at runtime. nginxinc/nginx-unprivileged is
# nginx's own maintained variant that already listens on 8080 (not the
# privileged port 80) and runs as a non-root user out of the box, so this
# doesn't need to hand-roll listen-port/permission changes on top of the
# stock nginx image. This app currently has no client-side router (no
# deep-linkable routes beyond "/"), so no SPA try_files fallback config is
# needed - the image's default static-file serving is sufficient as-is.
FROM nginxinc/nginx-unprivileged:stable-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
