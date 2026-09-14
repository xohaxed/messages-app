# Messages App — DevOps learning project

A small FastAPI + PostgreSQL service, carried through a full CI/CD pipeline
one stage at a time. Each stage exists to make the *next* tool obvious: do
the work by hand first, then watch the tool remove it.

**Current state: Stages 1–3 complete.**

| Stage | What | Status |
|-------|------|--------|
| 1 | App running locally, no Docker | done |
| 2 | Containerized by hand (`docker run`, network, volume) | done |
| 3 | Docker Compose, healthcheck gating, dev override | done |
| 4 | Jenkins in a container, building this image | next |
| 5 | AWS EC2, locked-down security group, deploy over SSH | |
| 6 | Trivy scan, smoke test, rollback path | |

---

## Quick start (Docker)

```bash
cp .env.example .env        # then set DB_PASSWORD
docker compose up -d --build
curl http://localhost:5000/health
```

Interactive docs: http://localhost:5000/docs

```bash
docker compose ps
docker compose logs -f
docker compose down         # volumes KEPT
docker compose down -v      # volumes DELETED — data gone
```

## Quick start (local, no Docker)

Requires PostgreSQL installed locally.

```bash
make bootstrap PGPW=your_postgres_superuser_password
make run
make test
```

`PGPW` is the superuser password chosen when installing PostgreSQL.
`APPPW` (default `change_me_local`) is the app user's password — you invent
it, and `DB_PASSWORD` in `.env` must match.

## API

| Method | Path | Returns | Notes |
|--------|------|---------|-------|
| GET | `/health` | 200 / 503 | 503 when the database is unreachable |
| GET | `/messages` | 200 / 503 | 100 most recent |
| POST | `/messages` | 201 / 422 / 503 | `{"author": "...", "content": "..."}` |
| DELETE | `/messages/{id}` | 204 / 404 / 503 | |

---

## Design decisions

Each of these is an interview answer. They are the point of the project.

### Application

**No default for the password, and `min_length=1`.** `app/config.py`. A
missing *or empty* `DB_PASSWORD` stops the app at startup with a clear
validation error. Without `min_length`, an empty value passes validation and
produces an endless `no password supplied` retry loop that looks like a
Postgres problem.

**The pool does not open at import time.** `open=False` in `app/db.py`. The
app must boot while the database is down, otherwise `/health` could never
report the outage — the process would simply die.

**`check=ConnectionPool.check_connection`.** Validates a pooled connection
before handing it to a request. Without it, connections to a database
container that was destroyed and recreated stay in the pool, and every
request fails until the app is restarted.

**`/health` actually queries the database, with a 2-second timeout.** An
endpoint returning `{"status":"ok"}` unconditionally is worse than none: the
deploy pipeline marks a broken release as successful. And a health check
that hangs for 30s makes a load balancer conclude the whole host is dead,
turning a blip into an outage.

**Database failures return 503, not 500.** `app/main.py` registers exception
handlers for `psycopg.Error` and `PoolTimeout`. 503 means "dependency down,
retry shortly"; 500 means "this code is broken". Monitoring, load balancers
and clients treat them very differently.

**SQL parameters, never f-strings.** `app/models.py` passes values as `%s`
with a tuple. That is the line between a query and an SQL injection.

**Pinned dependency versions.** `==`, not `>=`. A build that installs
whatever is newest today is a build that breaks on a Tuesday for reasons
nobody can reproduce.

**A pytest fixture, not a module-level TestClient.** `tests/conftest.py`.
FastAPI's lifespan (which opens the pool) only runs when `TestClient` is
used as a context manager. `client = TestClient(app)` at module level skips
it and every database call fails with "the pool is not open yet".

### Container

**Multi-stage build.** Build tools and pip caches stay in the builder stage.
~150 MB instead of ~1 GB: faster CI pulls, smaller CVE surface.

**`COPY requirements.txt` before `COPY app/`.** Dependency installation is
cached and only re-runs when requirements change. Reverse the two lines and
every build reinstalls everything.

**Non-root user.** Docker has no user namespace by default, so UID 0 in the
container is UID 0 on the host kernel. A container escape as root costs you
the machine.

**`--host 0.0.0.0`.** Bound to `127.0.0.1` the app would only accept
connections from inside its own container, and the port mapping would
silently do nothing.

**`PYTHONUNBUFFERED=1`.** Logs appear immediately instead of sitting in a
buffer. Without it `docker logs` looks empty during a crash — exactly when
it is needed.

**HEALTHCHECK using Python, not curl.** Slim images have no curl.

### Compose

**No `version:` key.** Obsolete in Compose v2; it only produces a warning.

**`depends_on` with `condition: service_healthy`.** Plain `depends_on` waits
for the container to *start*, not to be *ready*. Waiting on `pg_isready`
means no connection errors at startup. It governs startup only — a database
that dies later is what the 503 handler is for.

**`restart: unless-stopped`, not `always`.** With `always`, a container
deliberately stopped comes back after a Docker restart.

**Override file for development.** `docker-compose.override.yml` bind-mounts
the source and adds `--reload`; Compose merges it automatically. The base
file stays production-shaped, and the server deploys with
`docker compose -f docker-compose.yml up -d` so the override never loads.
Same repo, two behaviours, no `if ENV == "prod"` anywhere.

---

## Exercises worth repeating

**Dependency failure is handled, not fatal:**
```bash
docker compose stop messages-db
curl -i http://localhost:5000/health     # 503
curl -i http://localhost:5000/messages   # 503, not 500
docker compose start messages-db
curl -i http://localhost:5000/messages   # 200, no app restart needed
```

**Containers are disposable, volumes are not:**
```bash
docker compose rm -sf messages-db
docker compose up -d messages-db
curl http://localhost:5000/messages      # data still there
```

**DNS is the network:**
```bash
docker run --rm --network messages-app_messages-net alpine ping -c2 messages-db
docker run --rm alpine ping -c2 messages-db      # bad address
```

---

## Security notes

- `.env` is gitignored. Commit `.gitignore` **before** creating `.env` — a
  password that reaches git history must be rotated, not deleted.
- `change_me_local` is a local development password. It must never appear in
  a deployed environment. Stage 5 pulls credentials from the Jenkins
  credentials store.
- `make bootstrap PGPW=...` puts a password in shell history. Acceptable for
  a local database, never for anything real.
- Port 5433 is exposed to the host for convenience during development. On a
  real server the database port stays closed and is reachable only on the
  Docker network.

## Repository layout

```
.
├── app/                          application code
│   ├── config.py                 env-based settings, fails fast
│   ├── db.py                     connection pool + health probe
│   ├── models.py                 schemas and SQL
│   └── main.py                   routes and error handlers
├── tests/                        pytest suite (needs a live database)
├── db/init.sql                   schema
├── docker/Dockerfile             multi-stage, non-root
├── docker-compose.yml            production-shaped stack
├── docker-compose.override.yml   dev conveniences, auto-merged
├── scripts/setup_db.sh           local DB provisioning (Linux/macOS)
├── ci/                           Jenkinsfile lands here in Stage 4
└── Makefile                      cross-platform task runner
```

## Known limitations

Deliberate, and addressed in later stages.

- Tests require a live database. CI will need a throwaway Postgres service
  container (Stage 4).
- No migration tool. `docker-entrypoint-initdb.d` runs only on an empty
  volume, so schema changes after first boot are not applied. Alembic
  belongs here.
- No authentication on the API.
- No structured logging or metrics.
