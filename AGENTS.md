# AGENTS.md — Document Manager

Project instructions for AI agents and contributors working in this repository.

## Standing rule: version every change and push it

At the end of **every** user request in this repository:

1. **Bump the version** (Semantic Versioning, `MAJOR.MINOR.PATCH`):
   - `PATCH` — bug fixes, small UI/text tweaks, docs or tooling changes.
   - `MINOR` — new features or endpoints, backwards compatible.
   - `MAJOR` — breaking changes: rebrands, data/schema or API incompatibilities.
2. **Update every place the version appears** (they must match):
   - `backend/config.py` → `VERSION` (single source of truth; shown in the UI
     badge and in `GET /api/health`).
   - `Dockerfile` → `ARG APP_VERSION=<version>`.
   - `docker-compose.yml` → `image: document-manager:${APP_VERSION:-<version>}`.
3. **Add a `CHANGELOG.md` entry** under the new version with the date and a
   short `Added` / `Changed` / `Fixed` summary.
4. **Commit** the change together with the version bump, with a message that
   describes why the change was made.
5. **Tag and push**: create annotated tag `v<version>` and push both the branch
   and the tag to `origin` (`master`):

   ```bash
   git tag -a v<version> -m "Document Manager <version>"
   git push origin master
   git push origin v<version>
   ```

Do not leave a request committed but unpushed, or pushed without its version
bump and tag.

## Running the app

- Local Docker stack (app + MongoDB): `docker compose up --build` → http://localhost:5000
- Optional default admin: `docker compose exec app python seed.py` (`admin` / `admin123`)
- Version check: `curl http://localhost:5000/api/health` → `{"status":"ok","db":"connected","version":"..."}`

## Tests

Tests use pytest with an in-memory MongoDB (`mongomock`), so no database is
needed. Inside a running stack:

```bash
docker compose exec -T app sh -c "pip install -q -r requirements-dev.txt"
docker compose exec -T app python -m pytest -q tests
```

`requirements-dev.txt` holds the test-only dependencies and `tests/` is excluded
from the Docker build context.

## Auth model

- The JWT session token is an `HttpOnly`, `SameSite=Lax` cookie; page scripts
  never see it, and API calls need no `Authorization` header.
- Every HTML page is wrapped in `login_required_page`; APIs use `@jwt_required()`.
- The first account registered at `/register` becomes the admin; later public
  registrations are always customers. Admins create staff via `/api/users`.
- Do not expose tokens to `localStorage` or inline JSON responses again.

## Layout

- `backend/` — Flask + Socket.IO backend, Jinja templates, static assets.
- `backend/documents/` — uploaded PDFs (mounted volume in Docker).
- `requests/` — request/screenshot folders written by the request feature.
- `cse_app/` — Flutter mobile client (not deployed by Docker or the web app).
