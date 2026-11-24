# Security Policy

**Last reviewed:** 2026-11-24  
**Scope:** `RaulMunozz/flask-reservas` — Flask reservation form with an admin view, deployed on Render.

## Architecture

- Python/Flask application, SQLite via `sqlite3`, Bootstrap 5.3.0 from jsDelivr.
- Routes: `/` (public form), `/login`, `/logout`, `/reservas` (admin).
- SQL is parameterized; Jinja2 autoescaping is enabled.
- No file uploads, JSON API or CORS configuration.

## Findings fixed in this revision

| Severity | Finding | Fix |
|---|---|---|
| Critical | Session signing key hardcoded in public source | Key is now loaded from `SECRET_KEY`, with a random persistent local fallback for development. Production must set the variable. |
| Critical | Hardcoded plain-text admin credentials | Credentials removed from source. Login uses `ADMIN_USER` and `ADMIN_PASSWORD_HASH` with Werkzeug hashing and constant-time comparison. |
| High | CSRF on POST routes and logout via GET | CSRF token injected into all forms and verified for state-changing methods. `/logout` is POST-only. Session is rotated on login. |
| High | SQLite database with personal data committed to the repository | `reservas.db` removed from the current tree and ignored. The app creates the schema automatically on first run. |
| Medium | No browser security headers; CDN CSS without SRI | Added `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, restrictive CSP and optional HSTS. Bootstrap link now uses verified SRI. |
| Medium | Weak server-side validation and alignment to 15-minute slots | Length/format checks, date-not-in-past, and quarter-hour alignment enforced server-side. Request body limited to 8 KB. |
| Medium | Invalid legacy date values caused HTTP 500 | `todatetime` filter now returns `None` on malformed values and the template handles it safely. |
| Medium | No brute-force protection or login logging | Per-IP rate limit (5 attempts / 5 minutes) and failed-login logging. |
| Medium | EOL and unused dependencies | Updated Flask to 3.1.1, pinned Werkzeug, removed unused `sqlalchemy` and `psycopg2-binary`. |
| Low | No repository hygiene | Added `.gitignore` for databases, bytecode, IDE files and `.env`. |

## External configuration required for production

Set these in Render (or equivalent). Do **not** commit their values:

```text
SECRET_KEY=<random 32+ byte value>
ADMIN_USER=<admin username>
ADMIN_PASSWORD_HASH=<Werkzeug password hash>
SESSION_COOKIE_SECURE=1
HSTS=1
DATABASE_PATH=<path on persistent disk>
```

Generate a password hash without placing the plaintext in shell history:

```powershell
python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass()))"
```

`SESSION_COOKIE_SECURE=1` enables `Secure` cookies and the `__Host-session` name; it requires HTTPS end-to-end. `DATABASE_PATH` must point to persistent storage; otherwise reservations are lost on redeploy.

## Known limitations / pending external work

- **High — Git history:** earlier commits contained database blobs with real email addresses. Removing the file from the current tree does not rewrite history. Purge the blobs with `git filter-repo` in a coordinated maintenance window and rotate any reused credentials or contact data.
- **Medium — rate limit:** the in-memory limiter is per process and resets on restart. Add provider-level rate limiting/WAF for reliable protection.
- **Medium — persistence:** the free Render plan uses ephemeral storage. Use a persistent disk or a managed database. The removed unused Postgres dependencies can be restored if migrating to managed Postgres.
- **Low — CSP:** Bootstrap CSS is allowed from jsDelivr with SRI. Self-hosting it would allow removing that origin.
- **Low — no automated tests in repo:** verification was performed locally with a temporary test script; add permanent tests before major changes.

## Verification performed

- Python syntax check of `app.py`.
- Flask test client: GET `/` returns 200 with security headers; POST without CSRF token returns 400; malformed/ past reservations are rejected; unauthenticated `/reservas` redirects; valid login requires an externally supplied hash; logout is POST-only.
- SRI hash for Bootstrap 5.3.0 CSS recomputed from the CDN response.
- No hardcoded signing key or admin password remains in the current source tree.

## Maintenance

- Rotate the signing key and admin password if they were ever exposed.
- Keep `requirements.txt` pinned and review updates regularly.
- Re-run the local checks after changing routes, templates or dependencies.
- If a database with real personal data is reintroduced, never commit it.
