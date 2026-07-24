# Deployment Readiness

This note is the output of Milestone 11 (`docs/IMPLEMENTATION_ROADMAP.md` item 11: "Security
hardening, performance tests, observability, and deployment"). It lists what is genuinely still
missing before this platform could be operated in a real production environment, for computing
faculty at a real institution, with real exam content.

None of the items below were implemented as part of M11. Each one would require inventing a
requirement, policy, threshold, or deployment target that does not exist anywhere in this
repository's documentation - exactly the situation M11's implementation rules said to stop, explain,
and leave deferred, rather than guess at. This doc is that explanation, kept as a durable repository
artifact rather than left in a chat transcript, so the next milestone (or the person who eventually
deploys this) does not have to rediscover these gaps from scratch.

Each item states the current, verified state of the code/config (not a guess), why it stops short of
production-ready, and what kind of decision - not what specific product - would be needed to close it.

## Authentication
**Current state:** the only identity mechanism is the `X-Dev-User-Email` request header
(`backend/app/api/deps.py`), self-declared by the caller with no password, token, session, or
identity-provider verification of any kind. Any request bearing a syntactically valid email in that
header is auto-provisioned as that user (`get_or_create_faculty_user`) and gains that user's full
access to their own analyses.

**Why deferred:** no document in this repository specifies a real identity provider (institutional
SSO/OIDC, a local password store, etc.), a session/token strategy, or a login UI. Building any of
those now would mean inventing the institution's actual identity-integration requirements.

**What would close it:** a decision on how KAU faculty actually authenticate (existing institutional
SSO vs. a standalone credential store), which is an institutional/product decision, not an
engineering default this codebase can safely assume.

## TLS / transport security
**Current state:** `docs/SECURITY_AND_PRIVACY.md` states "Use TLS in deployed environments," but no
TLS termination exists anywhere in this repository - `docker-compose.yml` publishes both the backend
(8000) and frontend (5173) as plain HTTP, and no reverse proxy, certificate, or load balancer config
is present.

**Why deferred:** TLS termination is normally owned by whatever real hosting target receives the
traffic (a managed load balancer, an API gateway, a self-managed reverse proxy with real
certificates) - and no such target is documented (see "Real deployment target" below). Adding TLS
config now would mean inventing that target.

**What would close it:** picking a real hosting target, which then dictates the natural place for
TLS (e.g. a managed load balancer's own cert, or a reverse proxy in front of the containers built in
M11).

## Secrets management
**Current state:** secrets (`SECRET_KEY`, database credentials) flow through `.env` /
`docker-compose.yml`'s `env_file:`/`environment:` blocks, with only placeholder values in
`.env.example`. There is no vault, secrets manager, or encrypted-at-rest secret store integration.

**Why deferred:** no secrets-management product or policy is documented. This is standard and
adequate for local development (which is all this repository currently targets), not for a real
deployment.

**What would close it:** tied to the same "real deployment target" decision - most hosting platforms
and orchestrators provide their own secret-injection mechanism once chosen.

## Retention and deletion automation
**Current state:** `FILE_RETENTION_DAYS` (default 30) is defined in `.env.example` and
`app/core/config.py`, and `docs/SECURITY_AND_PRIVACY.md` names it explicitly - but no code anywhere
in `backend/app` reads this setting or deletes anything. There is no scheduled job, no deletion
endpoint, and no audit trail for deletions.

**Why deferred:** `docs/SECURITY_AND_PRIVACY.md` itself defers this ("Implement deletion jobs and
audit-safe metadata according to institutional policy before production use") - the institutional
retention policy it refers to is not specified anywhere in this repository.

**What would close it:** an actual institutional retention/deletion policy (how long, who can
request early deletion, what audit trail is legally/institutionally required), which this repository
has never had access to.

## Real deployment target
**Current state:** the only deployment artifact in this repository is `docker-compose.yml`, which is
oriented entirely at a single-host local development setup (bind-mounted source, published host
ports, named Docker volumes with no backup/replication story). M11 added named `production` build
stages to both Dockerfiles (non-root, no reload/dev-server), but nothing in this repository runs
those stages, and no cloud provider, orchestrator, or managed-database target is named anywhere in
the docs.

**Why deferred:** choosing a real target (which cloud, which managed Postgres/object-storage
offering, container orchestration vs. a single host, how ChromaDB is operated at that target) is a
product/infrastructure decision with real cost and vendor implications - not something inferable from
the current documentation.

**What would close it:** an explicit infrastructure decision from whoever owns hosting/budget for a
real deployment.

## Observability depth
**Current state:** logging is Python's standard `logging` module writing to stdout, following
`docs/SECURITY_AND_PRIVACY.md`'s safe-metadata-only rule (IDs, stages, durations, error classes - see
M11's new catch-all handler in `backend/app/core/errors.py` for the latest example of this pattern).
There is no log aggregation, metrics collection, distributed tracing, uptime monitoring, or alerting
configured or documented anywhere.

**Why deferred:** no document specifies what should page someone, what dashboard should exist, or
which metrics matter enough to collect - inventing an observability stack (Prometheus/Grafana vs. a
managed APM vendor, what counts as an alertable condition) without that would be pure guesswork.

**What would close it:** a decision on acceptable operational risk (what failure modes must be
noticed, and how quickly) from whoever will actually be on call for this system.

## Performance SLAs and load testing
**Current state:** `docs/SRS.md`'s only Performance NFR is qualitative ("background jobs and
progress polling," satisfied by the existing `BackgroundTasks`-based pipeline plus M11's new
contract-based test proving `POST /run` never blocks on pipeline execution -
`backend/tests/test_performance_non_blocking.py`). `docs/TEST_PLAN.md` defines no throughput,
concurrency, or latency target.

**Why deferred:** load-testing requires a target to test against (requests/second, acceptable p95
latency, expected concurrent users) - none is documented. Picking a number here would be exactly the
"undocumented performance threshold" M11's implementation rules said to avoid inventing.

**What would close it:** a real capacity requirement from whoever owns rollout (how many faculty,
how many concurrent analyses expected), which does not exist yet because this platform has not been
piloted with real users.

## Two gaps carried over from this milestone's own scope
Two sub-concerns considered during M11 itself were also descoped for the same reason - each is a
production-readiness gap in its own right, so they belong in this list too, not just in the
implementation's completion report:

- **No per-stage timeout or resource cap on the analysis pipeline.** `runner.py`'s existing
  generic exception handling safely fails on a malformed/hostile PDF that raises an exception (M11
  item 2 confirmed this already works, backed by existing tests) - but a pathological PDF that
  hangs or consumes excessive memory/CPU without raising is not caught by any timeout, because none
  exists. Adding one would mean inventing an undocumented duration/memory threshold.
- **No logging beyond the new catch-all for routine rejection paths** (validation 4xx responses,
  ownership/IDOR 404s). These already return safe, generic messages to the client (existing
  Problem-Details handlers), but M11 did not add structured logging for them, because no document
  specifies what such logs should capture or who/what would ever consume them - nothing in this
  repository currently reads application logs for security monitoring.

## What M11 actually delivered
For contrast, so this list reads as "what's left," not "what happened": M11 added a catch-all
exception handler with safe-message logging (`backend/app/core/errors.py`), confirmed the pipeline's
existing exception handling already fails safely on malformed/hostile PDFs, added a contract-based
test proving `POST /analyses/{id}/run` never blocks on pipeline execution, added report-only
dependency-vulnerability scanning to CI (`pip-audit`, `npm audit`), and hardened both Dockerfiles
with non-root, non-reload `production` build targets alongside the unchanged `dev` targets. See the
implementation's completion report for the full file-by-file breakdown.
