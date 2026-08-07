# Security and Privacy

## Upload controls
Validate extension, declared MIME, PDF magic bytes, maximum size, parser readability, file count, and safe filename handling. Use generated storage keys and quarantine before processing.

## Authentication and authorization
Faculty Members register with email and password. Passwords are Argon2id-hashed and never logged.
Signed bearer tokens include expiry, issuer, audience, and a server-checked token version. Logout
and password reset revoke earlier access tokens. Password-reset tokens are random, stored only as
SHA-256 hashes, expire, and are single-use.

Every analysis, file, evidence item, finding, and report is scoped to its Faculty Member owner.
Download endpoints re-check ownership authorization and cross-owner requests return the same 404 as
a missing resource. Staging/production must add rate limiting and security monitoring at the
deployment boundary.

## Data protection
Use TLS in deployed environments, encrypted managed storage where available, database encryption controls, strong secrets, and least-privilege service accounts.

## Logging
Log IDs, stages, durations, error classes, and safe summaries. Do not log full exam/Course Specification text, prompts containing source content, passwords, access tokens, password-reset tokens, API keys, or signed download URLs.

## Retention
Default configurable retention is documented through `FILE_RETENTION_DAYS`. Implement deletion jobs and audit-safe metadata according to institutional policy before production use.

## AI providers
Do not send files to an external provider unless the deployment's privacy policy permits it. Minimize payloads, disable provider training where supported, document region/retention, and provide a local or approved-provider adapter.

## Threats to test
Path traversal, MIME spoofing, oversized/decompression attacks, malicious PDFs, prompt injection within uploaded documents, cross-tenant access, report URL leakage, model-output injection, and dependency vulnerabilities.
# Extraction and artifact privacy additions

- Examination OCR is local Tesseract behind a provider-neutral interface; no
  cloud OCR provider or OCR credential is configured.
- Optional extraction Gemini receives complete selected exam-page images plus
  normalized lines, token geometry, local candidates, and warnings only when
  explicitly enabled. It is governed separately from academic evaluation, and
  deployment privacy approval must cover that transfer before enabling it.
- Validated Gemini structure output may be cached beside the owner-scoped
  upload to preserve quota. The cache is private exam data, is not logged or
  source-controlled, and is deleted with the analysis. Cache keys contain only
  hashes of the document/model/prompt inputs.
- The exam preview API enforces analysis ownership and returns bytes without
  exposing storage keys or local paths.
- Permanent analysis deletion uses server-resolved paths only. Database
  deletion is authoritative; physical artifact removal is best effort and a
  missing file is safe.
