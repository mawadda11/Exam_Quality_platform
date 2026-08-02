# Production/Staging Deployment

Single-server Docker Compose deployment for a staging or controlled-pilot
production environment. This document covers `docker-compose.prod.yml`
only; `docker-compose.yml` (development) is unaffected and still works as
described in `README.md`/`CLAUDE.md`.

This is a single-server deployment guide. It intentionally does not cover
Kubernetes, Terraform, any cloud-managed service, or a CI/CD pipeline - see
`docs/V2_ROADMAP.md` for whether/when that scope is planned.

## A. Architecture (text diagram)

```
                              Internet
                                 |
                          (ports 80, 443 only)
                                 v
                       +-------------------+
                       |    reverse-proxy   |   Caddy, automatic HTTPS
                       |   (Caddy, pinned)   |   for a real domain
                       +-------------------+
                          |              |
                 /api/*   |              |  everything else
                          v              v
                  +--------------+  +--------------+
                  |   backend     |  |   frontend    |
                  |  FastAPI       |  | nginx (static |
                  |  :8000 (int.)  |  | build) :8080  |
                  +--------------+  +--------------+
                     |         |
                     |         +----------------------------+
                     v                                      v
              +-------------+                    +----------------------+
              |  postgres    |                    |     chromadb          |
              |  :5432 (int.) |                    |  1.5.9, :8000 (int.)  |
              +-------------+                    +----------------------+

              +-------------+     +-------------+
              |  migrate     |     | storage-init |  one-shot, root only:
              |  (backend    |     |  (backend    |  chown/chmod the
              |   image)     |     |   image)     |  uploads/reports
              +-------------+     +-------------+  volumes, then exits
               both run before backend starts and must both exit 0

  Deployment host (outside Compose):
   Ollama server, model qwen3.5:4b, port 11434 - reachable from the
   backend container ONLY via host.docker.internal, never published,
   never a Compose service.
```

Only `reverse-proxy` publishes ports (80/443). `postgres`, `chromadb`,
`backend`, and `frontend` are reachable only from other containers on the
Compose network, by their Compose service name.

## B. Prerequisites

- A Linux server (bare metal or VM) you control, with a public IP if you
  intend to serve a real domain.
- Docker Engine and the Docker Compose plugin (`docker compose version`
  should report a v2 client).
- A domain name pointed at the server (staging/production only - the local
  smoke test needs neither a domain nor a public server).
- Enough disk for PostgreSQL data, ChromaDB data, uploaded exams/TP-153
  files, and generated reports; size according to your expected pilot
  volume and `FILE_RETENTION_DAYS`.
- Outbound network access from the host for pulling Docker images (Ollama
  itself needs no outbound access once its model is pulled).

## C. Required server software

- Docker Engine (with the `docker compose` plugin, not the standalone
  `docker-compose` v1 binary).
- Git (to check out this repository on the server).
- `curl` (used by `deploy/scripts/deploy.sh` and `health-check.sh` to poll
  the health endpoint; present on essentially every Linux distribution or a
  one-line package install away).
- Ollama, installed directly on the host (not in a container) - see the
  next section.

## D. Ollama installation and model pull

Ollama runs on the deployment host itself, outside Docker, and is never
published on any public port. The backend container reaches it through
Docker's host-gateway alias (`host.docker.internal`), which
`docker-compose.prod.yml`'s `backend.extra_hosts` entry makes resolve on
Linux Docker Engine too (it is automatic on Docker Desktop).

1. Install Ollama on the host following the vendor's official Linux
   installation instructions for your distribution.
2. Pull the approved model:
   ```bash
   ollama pull qwen3.5:4b
   ```
3. Confirm it is present:
   ```bash
   ollama list
   ```
4. Ensure the Ollama service starts on boot and keeps running continuously
   - the backend calls it for every semantic evaluation, so if it is
   stopped, semantic AI calls fail safely (a processing failure, never an
   academic status - see `docs/AI_GOVERNANCE.md`) until it is running again.
   Most Ollama Linux installers register a systemd service for this
   automatically; verify with `systemctl status ollama` (or your
   distribution's equivalent) and enable it if it is not already enabled.
5. Never configure a firewall rule that exposes port 11434 outside the
   host. It does not need to be reachable from anywhere except this same
   machine's Docker containers.

### Known JSON-Schema compatibility behavior (Ollama 0.32.5 / qwen3.5:4b)

Some Ollama/model combinations reject the full JSON-Schema structured-output
request with HTTP 400 ("Failed to initialize samplers: failed to parse
grammar"). This is handled automatically: `OllamaProvider` detects exactly
this confirmed condition and retries once with Ollama's simpler
`format="json"` mode - no operator action is required, no analysis fails
because of it, and no secrets or document content are exposed while
detecting it. See `docs/RAG_AND_AI_DESIGN.md`'s "Ollama JSON-mode
compatibility fallback" for the full detection/fallback contract. If an
analysis still fails at `applying_rules` with a provider error, check
`docker compose ... logs backend` for the (sanitized, content-free)
`AiProviderError` message - it distinguishes this compatibility case from a
genuine Ollama outage (timeout, connection failure, model not pulled).

## E. Domain DNS setup

Point an `A` (and/or `AAAA`) record for your chosen domain (e.g.
`exam-quality.your-institution.edu`) at the server's public IP address.
Caddy performs automatic ACME HTTP-01/TLS-ALPN validation against ports
80/443 the first time it starts with a real domain in `CADDY_SITE_ADDRESS`,
so DNS must already be propagated and ports 80/443 reachable from the
internet before first start - otherwise certificate issuance fails (Caddy
retries automatically; it does not crash-loop the rest of the stack).

## F. Creating `.env.production` safely

**Never edit the tracked `.env.production.example` in place with real
values, and never commit `.env.production`.**

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Then edit `.env.production` (not the `.example` file) and replace every
placeholder listed in its comments: `APP_DOMAIN`, `CADDY_SITE_ADDRESS`,
`SECRET_KEY`, `POSTGRES_PASSWORD` (and the matching password inside
`DATABASE_URL`), `ALLOWED_ORIGINS`, `PASSWORD_RESET_URL`, and the `SMTP_*`
block. `.env.production` already matches this repository's `.env.*`
`.gitignore` pattern, so `git status` should never show it as trackable;
if it ever does, stop and fix `.gitignore` before proceeding.

## G. Generating a strong `SECRET_KEY`

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the output as `SECRET_KEY` in `.env.production`. It must be at least
32 characters - `backend/app/core/config.py:validate_runtime_settings`
refuses to start in `production`/`staging` with anything shorter or with
the literal placeholder value from `.env.production.example`.

## H. PostgreSQL password requirements

- Never reuse the development stack's `exam_quality` password.
- Use a long, random, unique password - e.g.
  `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
- Set the same value in both `POSTGRES_PASSWORD` and inside the
  `DATABASE_URL` connection string in `.env.production` - they must match
  exactly, since one configures the database server and the other is how
  the backend authenticates to it.
- Avoid characters that need special shell/URL escaping if you edit
  `DATABASE_URL` by hand (a `token_urlsafe` value is already safe).

## I. SMTP requirements

`validate_runtime_settings` requires `SMTP_HOST` and `SMTP_FROM_EMAIL` to be
set whenever `APP_ENV` is `staging` or `production` - password reset has no
development-only debug-token fallback outside `development`. You need a
real SMTP relay (institutional mail server, or a transactional-email
provider) with:

- `SMTP_HOST`, `SMTP_PORT` (587 for STARTTLS is the default here),
- `SMTP_USERNAME`/`SMTP_PASSWORD` if your relay requires authentication,
- `SMTP_FROM_EMAIL` set to an address your relay is authorized to send as,
- `SMTP_USE_TLS=true` unless your relay specifically requires plaintext
  (not recommended).

For the **local production smoke test only** (never real staging/
production), see section 15 below for placeholder SMTP values that satisfy
this startup check without an actual mail server.

## J. Building and starting the stack

From the repository root, with `.env.production` already created (section
F) and Ollama already running on the host (section D):

```bash
deploy/scripts/deploy.sh
```

This validates the required environment variables (without printing their
values), validates the Compose configuration, builds the production images,
runs database migrations, starts the stack, and waits for
`/api/v1/health` to respond successfully. See section 15 for the exact
commands to run this against `localhost` first.

To run the equivalent steps by hand instead:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml build
docker compose --env-file .env.production -f docker-compose.prod.yml up migrate --exit-code-from migrate --abort-on-container-exit
docker compose --env-file .env.production -f docker-compose.prod.yml up storage-init --exit-code-from storage-init --abort-on-container-exit
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

## K. Running migrations and storage initialization

Migrations run automatically as part of `deploy.sh`/the commands above, via
the one-shot `migrate` service (`alembic upgrade head`), which the
`backend` service depends on with `condition: service_completed_successfully`
- backend will not start until migrations have applied cleanly. To run
migrations again by hand later (e.g. after pulling a new commit with new
migrations, before restarting the rest of the stack):

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up migrate --exit-code-from migrate --abort-on-container-exit
```

### Why storage initialization is required

`backend_uploads` and `backend_reports` are Docker named volumes. The very
first time Docker creates a named volume, it is owned by `root`. The
`backend` container runs as a fixed non-root UID (`10001:10001`, set in
`backend/Dockerfile`'s production stage) and must stay that way - so
without an extra step, the first upload after a fresh deployment fails with
exactly the error this section exists to prevent:

```
PermissionError: [Errno 13] Permission denied: '/app/storage/uploads/...'
```

The one-shot `storage-init` service fixes this: it runs the *same*
production backend image, but with a Compose-level `user: "0:0"` override
that applies **only to this one service** (backend/migrate are unaffected
and still run as UID 10001). It mounts the exact same `backend_uploads`/
`backend_reports` volumes as `backend`, then runs `mkdir -p` (a no-op if the
directories already exist), `chown -R 10001:10001`, and `chmod -R 0750`
(owner read/write/execute, group read/execute, no access for anyone else -
never `0777`) before exiting. `chown`/`chmod` never touch file contents, so
re-running this on every deploy against an already-populated volume is safe
and preserves existing uploads/reports. `backend` depends on it with
`condition: service_completed_successfully`, exactly like `migrate`.

Run it again by hand the same way as migrations:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up storage-init --exit-code-from storage-init --abort-on-container-exit
```

### Expected state

After a successful deploy, `storage-init` (like `migrate`) is a stopped
container with exit code 0 - this is normal, not a crash:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps -a storage-init
# STATUS column should read "Exited (0) ..."
```

### Troubleshooting (safe commands - no secrets printed)

```bash
# Did it actually succeed?
docker compose --env-file .env.production -f docker-compose.prod.yml ps -a storage-init

# What did it do/say?
docker compose --env-file .env.production -f docker-compose.prod.yml logs storage-init

# Confirm ownership/mode directly (safe: only shows file metadata, never
# uploaded document content).
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm storage-init \
  sh -c "ls -ld /app/storage/uploads /app/storage/reports"
# Expect: drwxr-x--- ... 10001 10001 ... for both.
```

### Write-permission smoke test

Confirms the non-root `backend` container can actually create a file in
each volume - the exact operation that used to fail with `PermissionError`:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend \
  sh -c "touch /app/storage/uploads/.write-test && touch /app/storage/reports/.write-test && echo WRITE_OK"
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend \
  sh -c "rm -f /app/storage/uploads/.write-test /app/storage/reports/.write-test"
```

`WRITE_OK` confirms both directories are writable by the backend's own
non-root user. If this fails, re-run `storage-init` (above) and retry.

## L. Health verification

```bash
deploy/scripts/health-check.sh
```

Checks the public `/api/v1/health` endpoint through the reverse proxy (as a
real client would reach it) and every container's own health/status,
without printing any secret values. Or by hand:

```bash
curl -f https://your-domain/api/v1/health
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

## M. Log inspection

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f backend
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f reverse-proxy
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=200 migrate
```

Per `docs/SECURITY_AND_PRIVACY.md`, application logs are designed to never
include full exam/TP-153 text, prompts containing source content, model
responses, passwords, tokens, or environment values - if you ever see any
of those in the logs, treat it as a bug and stop relying on the logs for
anything sensitive until it is fixed.

## N. Backup procedure

```bash
deploy/scripts/backup.sh
```

Requires the stack to be running (it reads the live PostgreSQL database and
the backend container's mounted storage). Produces a timestamped directory
under `deploy/backups/<UTC timestamp>/` (gitignored, not served publicly)
containing `postgres.sql`, `uploads.tar.gz`, and `reports.tar.gz`. No
secrets are written into the backup contents beyond what the database
itself already stores (password hashes, not plaintext passwords - see
`docs/SECURITY_AND_PRIVACY.md`). Retention/rotation is a deliberate manual
decision - see the comment at the top of `deploy/scripts/backup.sh` for a
one-line pruning command once you are ready to adopt one; schedule
`backup.sh` itself with cron or systemd timers according to your
institution's retention policy.

## O. Restore drill

Practice this on a disposable/staging copy of the stack before you ever
need it for real.

```bash
deploy/scripts/restore.sh \
  --db-dump deploy/backups/<timestamp>/postgres.sql \
  --uploads-archive deploy/backups/<timestamp>/uploads.tar.gz \
  --reports-archive deploy/backups/<timestamp>/reports.tar.gz
```

Run once **without** `--confirm` first - it prints the restore plan and
exits without changing anything, so you can double-check the paths. Add
`--confirm` to actually restore. Restoring PostgreSQL into a database that
already has conflicting data can fail with constraint errors rather than
silently overwriting it (the script never runs `DROP DATABASE`); for a
clean restore drill, restore into a freshly provisioned stack (new
`postgres_data`/`backend_uploads`/`backend_reports` volumes) rather than
one with existing data.

## P. Updating to a new Git commit

```bash
cd /path/to/checkout
git fetch origin
git checkout <new-commit-or-tag>
deploy/scripts/deploy.sh
```

`deploy.sh` rebuilds images from the new commit, runs any new migrations
before starting the new backend, then starts the updated stack. Named
volumes (`postgres_data`, `chroma_data`, `backend_uploads`, `backend_reports`,
`caddy_data`, `caddy_config`) persist across this - nothing in the update
path touches them directly. Consider running `deploy/scripts/backup.sh`
immediately beforehand (see section N).

## Q. Rolling back safely

1. Take a backup first if you have not already (section N) - a rollback
   after a failed migration can itself need recovery.
2. `git checkout <previous-known-good-commit-or-tag>`.
3. Re-run `deploy/scripts/deploy.sh`.

Alembic migrations in this project are forward-only in normal operation
(`CLAUDE.md`: "Database migrations already deployed: never rewrite; create
a new migration"), so rolling back the *application code* to a commit whose
migrations are a strict prefix of what is already applied is safe (older
code against a newer-but-compatible schema is the normal expectation this
project's migration discipline is built around). Rolling back across a
migration that made a breaking, non-additive schema change is not something
`deploy.sh` can undo automatically - restoring the pre-migration backup
(section O) is the safe path in that specific case.

## R. Stopping the stack

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

This stops and removes containers but **keeps all named volumes** (data
persists). To also remove volumes (irreversible - only do this when you
genuinely intend to delete all data, e.g. decommissioning an environment):

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down --volumes
```

## S. Security checklist

- [ ] `.env.production` is not tracked by Git (`git status` shows it as
      untracked/ignored, never staged).
- [ ] `SECRET_KEY` is a real random value, at least 32 characters, not the
      placeholder.
- [ ] `POSTGRES_PASSWORD` is a real random value, not `exam_quality` or the
      placeholder, and matches the password embedded in `DATABASE_URL`.
- [ ] `APP_ENV=production` (or `staging`) - never `development` outside a
      dev environment.
- [ ] `ALLOWED_ORIGINS` names the exact real origin(s) only - no wildcards.
- [ ] SMTP is a real, working relay - no debug reset-token behavior is
      possible outside `development` (`validate_runtime_settings` enforces
      this at startup).
- [ ] `/docs`, `/redoc`, and `/openapi.json` are unreachable
      (`curl -f https://your-domain/docs` should fail) - confirmed by
      `backend/app/main.py`'s environment-based gating.
- [ ] PostgreSQL, ChromaDB, the backend, and Ollama are not reachable from
      outside the host (`docker compose ps` shows no published ports for
      `postgres`/`chromadb`/`backend`; `ollama list` only works locally on
      the host; no firewall rule opens 5432/8000/11434 publicly).
- [ ] Only ports 80 and 443 are open to the internet on this host.
- [ ] TLS is active (a real `CADDY_SITE_ADDRESS` domain, not `http://`) for
      any deployment reachable from the public internet.
- [ ] `knowledge_base/` is mounted read-only into the backend container
      (`docker inspect` the backend container's mounts, or trust
      `docker-compose.prod.yml`'s `:ro` suffix on that mount).
- [ ] Backups exist and a restore drill has been performed at least once
      (sections N/O).

## T. Staging acceptance checklist

Run this against a real staging deployment (a real domain is not required -
the local smoke test in section 15 is an acceptable stand-in for "staging"
if you have no separate staging server) before promoting to production:

- [ ] `deploy/scripts/deploy.sh` completes without error end-to-end.
- [ ] `deploy/scripts/health-check.sh` reports every container healthy.
- [ ] A Faculty Member can register, sign in, and request a password reset
      email that actually arrives (proves SMTP works end-to-end, not just
      that the startup validation passed).
- [ ] A full analysis (upload exam + TP-153, Extraction Review confirmation,
      governed evaluation, PDF report download) completes successfully
      using the configured `AI_PROVIDER=ollama` adapter - confirms Ollama on
      the host is reachable from the backend container.
- [ ] `deploy/scripts/backup.sh` then `deploy/scripts/restore.sh --confirm`
      succeed against a disposable copy of the stack (section O).
- [ ] React Router deep links (e.g. reloading the browser on an in-app
      results page URL, not just the root) load correctly through the
      reverse proxy rather than 404ing.
- [ ] The security checklist (section S) is fully checked off.

## U. Production go/no-go checklist

- [ ] Everything in the staging acceptance checklist (section T) passed on
      this same server/configuration, not just a different environment.
- [ ] DNS for the real production domain is propagated and TLS certificate
      issuance has succeeded (`docker compose logs reverse-proxy` shows no
      ACME errors).
- [ ] A recent backup exists (taken after staging acceptance, before real
      user data accumulates).
- [ ] `docs/PILOT_ACCEPTANCE_CHECKLIST.md` and `docs/KNOWN_LIMITATIONS.md`
      have been reviewed for anything beyond infrastructure readiness (this
      document covers deployment only, not product/governance readiness).
- [ ] An on-call/monitoring owner is identified for this deployment -
      `deploy/scripts/health-check.sh` is only useful if someone actually
      runs it (or a scheduler runs it) periodically.
- [ ] Rollback steps (section Q) have been reviewed by whoever is deploying,
      not just written down.

---

## 15. Local production smoke test

Test the *production* Compose stack (real production Docker targets, no
`--reload`, no bind-mounted source, Caddy in front) entirely on your own
machine, with no domain and no public exposure, before ever touching a real
server.

```bash
cp .env.production.example .env.production
```

Edit `.env.production` and override just these values (everything else can
keep its `.env.production.example` default *except* `SECRET_KEY` and
`POSTGRES_PASSWORD`, which still must be changed away from the placeholders
- `validate_runtime_settings` enforces this even for a local smoke test
since `APP_ENV=production` is unchanged):

```
CADDY_SITE_ADDRESS=http://localhost
APP_DOMAIN=localhost
ALLOWED_ORIGINS=http://localhost
PASSWORD_RESET_URL=http://localhost/reset-password
```

**SMTP for the smoke test only:** real staging/production requires a
working SMTP service (section I) - password reset will not actually
deliver email without one. To get past `validate_runtime_settings`'s
startup check for a local smoke test where you do not care whether reset
email really sends, placeholder-but-non-empty values are enough:

```
SMTP_HOST=localhost
SMTP_FROM_EMAIL=noreply@localhost
```

Then generate and set a real `SECRET_KEY` (section G) and a real
`POSTGRES_PASSWORD` (section H, matched into `DATABASE_URL`) - do not skip
this even for a local test, since it is exactly what proves
`validate_runtime_settings` is wired up correctly.

Validate and start:

```bash
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
deploy/scripts/deploy.sh
```

Then open `http://localhost` in a browser, and/or:

```bash
curl -f http://localhost/api/v1/health
deploy/scripts/health-check.sh
```

Tear down afterward the same way as a real deployment (section R); add
`--volumes` if you want a completely clean slate for a repeat test.
