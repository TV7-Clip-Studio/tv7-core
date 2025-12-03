# Security & Secrets Guidelines (Cross-Repo)

Secrets
- Never commit secrets. Use env vars, secret managers, or CI secrets.
- Do not log secrets or tokens. Redact before logging.
- Avoid storing long-lived tokens on disk; prefer ephemeral/session tokens.

Auth/crypto
- Use HTTPS/TLS everywhere. License tokens are JWT-like and signed.
- Rotate keys/secrets regularly; document rotation steps per repo.

Access boundaries
- Engine stays local-only (no network, loopback bind only).
- Backend stores social tokens server-side; least privilege scopes.

Dependencies
- Pin critical dependencies; run security scans (Bandit/Ruff for backend, cargo-audit, npm/yarn audits, Flutter advisories).

Build/release
- Sign binaries where applicable.
- Verify artifacts in CI; avoid downloading unpinned artifacts at runtime.
