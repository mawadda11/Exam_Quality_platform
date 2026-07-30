# Version 2 Batch 1 Implementation Report

**Included milestones:** M0 + M1  
**Branch target:** `develop/v2.0.0-arabic-pilot`

## Delivered

### Governance foundation

- Added `docs/V2_M0_ARCHITECTURE_DECISIONS.md`.
- Frozen authentication, ownership, Arabic acceptance, Course Specification, rule, and question-classification boundaries.

### Backend authentication

- Public Faculty Member registration.
- Email/password login.
- Current-user endpoint.
- Logout with token-version revocation.
- Password reset request and single-use confirmation.
- Argon2id password hashing.
- Signed bearer access tokens with issuer, audience, expiry, and token-version validation.
- Generic password-reset response to reduce account enumeration.
- SMTP adapter for staging/production reset delivery.
- Startup checks for strong production secrets and SMTP configuration.

### Persistence

Migration `0009` adds:

- `users.password_hash`;
- `users.is_active`;
- `users.email_verified`;
- `users.token_version`;
- `users.last_login_at`;
- `password_reset_tokens` with hashed token, expiry, and single-use state.

Existing Version 1 users remain unclaimed with a nullable password hash; no credential is invented for them.

### Authorization and isolation

- Removed the runtime `X-Dev-User-Email` trust model.
- All analysis/report ownership dependencies now require a verified bearer token.
- Existing owner-safe `404` behavior remains unchanged.
- Existing analysis creation continues deriving `user_id` from the authenticated user.
- Worker tasks continue accepting only `analysis_id`, preserving browser-session independence.

### Frontend

- Added sign-in, registration, forgot-password, and reset-password routes.
- Added persistent bearer-token session restoration.
- Added protected application routes.
- Added signed-in faculty account panel and sign-out action.
- Removed the development identity bar from the application shell.
- Dashboard and history remain backed by the owner-filtered API.

## Deliberately not included in Batch 1

- Arabic extraction/OCR runtime changes.
- Adaptive Course Specification parsing.
- Six deferred/unsupported rules.
- Question-type analytics.
- Full Arabic/English UI and reports.
- Email verification workflow.
- Institution/admin roles.
- Production deployment infrastructure.

## Operational note

Development and test environments can return a debug password-reset token because no SMTP service is required locally. Staging/production fail startup unless SMTP is configured. Reverse-proxy/API-gateway rate limiting is still required before opening the pilot beyond controlled use.
