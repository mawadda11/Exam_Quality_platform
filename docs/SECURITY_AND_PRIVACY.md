# Security and Privacy

## Upload controls
Validate extension, declared MIME, PDF magic bytes, maximum size, parser readability, file count, and safe filename handling. Use generated storage keys and quarantine before processing.

## Authorization
Every analysis, file, evidence item, finding, and report is scoped to its owner or permitted institutional role. Download endpoints re-check authorization.

## Data protection
Use TLS in deployed environments, encrypted managed storage where available, database encryption controls, strong secrets, and least-privilege service accounts.

## Logging
Log IDs, stages, durations, error classes, and safe summaries. Do not log full exam/TP-153 text, prompts containing source content, API keys, or signed download URLs.

## Retention
Default configurable retention is documented through `FILE_RETENTION_DAYS`. Implement deletion jobs and audit-safe metadata according to institutional policy before production use.

## AI providers
Do not send files to an external provider unless the deployment's privacy policy permits it. Minimize payloads, disable provider training where supported, document region/retention, and provide a local or approved-provider adapter.

## Threats to test
Path traversal, MIME spoofing, oversized/decompression attacks, malicious PDFs, prompt injection within uploaded documents, cross-tenant access, report URL leakage, model-output injection, and dependency vulnerabilities.
