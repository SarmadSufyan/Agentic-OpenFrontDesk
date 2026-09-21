# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report privately via **GitHub Security Advisories** ("Report a vulnerability" on the repo's
Security tab). Include steps to reproduce and impact. We'll acknowledge and work on a fix; responsible
disclosure is appreciated.

## Supported versions

This project is in **alpha** — security fixes target the `main` branch.

## Security posture (implemented)

- bcrypt password hashing; short-lived JWT access tokens + refresh.
- Membership-enforced multi-tenant isolation (every tenant-owned query is scoped).
- PII redaction in logs (emails, phone numbers).
- Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
- Per-tenant rate limiting (Redis).
- Uploaded documents are treated as **data, never instructions** (prompt-injection mitigation).

See [`docs/13-security-compliance.md`](docs/13-security-compliance.md) for the full model, the threat
table, and the planned items (recording consent, secret encryption-at-rest, audit hardening).

## Handling secrets

Never commit real secrets. `.env` is git-ignored; use `.env.example` as the template. For sensitive or
paying clients, run the fully self-hosted provider stack so no third party sees call data.
