# Experiment 08: Integration Testing

**Date**: 2026-11-22
**Suite**: `tests/integration/test_integration.py` (+ `tests/integration/conftest.py`)
**Result**: ✅ **26/26 integration tests pass** (37/37 including this directory's performance suite)

## Overview

Ten end-to-end integration tests were executed across every openScience
service boundary.  Each test runs a real scenario (no mocks for the units
under test) and verifies that components interoperate correctly.  Three
integration bugs in production code were found and fixed; several
agent/skill contract mismatches were documented and either fixed or
explicitly worked around in tests.

| # | Integration Test | Result |
|---|------------------|--------|
| 1 | Complete workflow: load → analyze → visualize → write | ✅ |
| 2 | Docker + API + Database integration | ✅ |
| 3 | API + Agent + Worker integration | ✅ |
| 4 | UI + API integration | ✅ |
| 5 | Session persistence across services | ✅ |
| 6 | Error propagation across services | ✅ |
| 7 | Logging across services | ✅ |
| 8 | Monitoring and metrics | ✅ |
| 9 | Backup and recovery | ✅ |
| 10 | Upgrade path (Alembic) | ✅ |

---

## Test 1 — Complete workflow: load → analyze → visualize → write

**Scenario** (`TestCompleteWorkflow::test_load_analyze_visualize_write`)

- Runs the core `ScienceSession` pipeline end-to-end in-process:
  `load_data()` → `analyze()` → `visualize()` → `write_methods()`.
- Repeats the identical four steps through the REST API
  (`POST /sessions/{id}/load|analyze|visualize|write`).
- Asserts task history via `GET /sessions/{id}/results`:
  task types `["load", "analyze", "visualize", "write"]`, all `completed`.

**Components crossed**: `ScienceSession` → `AgentOrchestrator` →
`Sandbox._run_awaitable` → agents (`data_ingestor`, `qc_analyzer`,
`publication_formatter`, `methods_writer`) → FastAPI routes → SQLAlchemy
task records.

**Bugs found & fixed**

| Bug | Fix |
|---|---|
| `scientific_writing._write_methods()` crashed with `AttributeError: 'Result' object has no attribute 'get'` when handed a framework `Result` (orchestrator output). | Unwrap `result.data` when a `Result`-like object is passed. |
| `matplotlib_skill.render()` rejected `viz_type="auto"` even though `Session.visualize(type="auto")` is the documented default, then crashed on nested skill envelope dicts. | Added an `_auto` builder: unwraps nested `{"data": ...}` envelopes, box-plots numeric frames, and emits a text-summary figure for stub payloads; `render()` maps `"auto"` → `_auto` and unwraps `Result` objects. |

---

## Test 2 — Docker + API + Database integration

**Scenario** (`TestDockerAPIIntegration`)

- Spins up a real Postgres 16 container via `docker compose -p openscience-it08`
  (`--wait` for healthcheck green: `pg_isready`).
- Verifies the container is running via `docker compose ps --format json`.
- Connects with `psycopg2`, then runs the **real** `init_db()` schema creation
  against the container and asserts `users/agents/sessions/tasks` exist.
- Fixture tears down with `docker compose down -v`.

**Skips**: if the Docker CLI or daemon is unavailable (graceful `pytest.skip`).

**Result**: ✅ passes (~4 s with the local daemon).

---

## Test 3 — API + Agent + Worker integration

**Scenario** (`TestAPIAgentWorkerIntegration`)

- API startup registers all **111 agents** into the `agents` table; the test
  reads them back via `/api/v1/agents` and `/api/v1/agents/{name}` and checks
  all seven categories (`literature`, `experiment`, `data_management`,
  `analysis`, `visualization`, `writing`, `review`).
- Runs the Celery `analyze_data_task` eagerly (no broker needed) on real CSV
  data — agent orchestration goes through the same `ScienceSession.analyze`
  path the API uses. Worker `health_check` returns `{"status": "healthy"}`.
- End-to-end chain: API session load on a dataset, then the worker analyzes
  the **same file**; both layers agree on the `qc_analyzer` capability listed
  via `/api/v1/analysis/capabilities`.

**Bug found & fixed**

`Sandbox._apply_limits` called `resource.setrlimit(RLIMIT_AS/RLIMIT_CPU, ...)`
unconditionally. On macOS the hard limits are `RLIM_INFINITY`; tightening them
raises `ValueError: current limit exceeds maximum limit`, crashing **every**
sandboxed run on macOS dev machines (worker tasks, sessions). Wrapped the
limit application/restoration in best-effort `try/except (OSError, ValueError)`
(resource limits are still enforced by the container runtime in production).

---

## Test 4 — UI + API integration

**Scenario** (`TestUIAPIIntegration`)

- Builds the real Flask app (`openscience.server.create_app`) and asserts:
  - `GET /` serves the openScience HTML page;
  - `GET /api/agents` returns the agent list consumed by the React UI —
    cross-checked against `ui/src/App.jsx` (`axios.get('/api/agents')`,
    `response.data.agents`);
  - `POST /api/session/load` + `/api/session/analyze` run end-to-end;
  - `GET /health` returns `{"status": "healthy", "service": "openscience-api"}`.

**Notes**: the source check degrades gracefully if the `ui/` tree moves.

---

## Test 5 — Session persistence across services

**Scenario** (`TestSessionPersistence`)

- **Framework level**: `ScienceSession.save()` → new
  `ScienceSession.load()`; `_data`, `_results`, and `project_dir` round-trip
  byte-for-byte.
- **Database level across "restarts"**: create a session + load + analyze via
  the API, exit the app, create a **fresh** `FastAPI` app on the same SQLite
  file. Session metadata, `data_keys`, and full task history survive; the
  lazily-rebuilt live session accepts further `/analyze` calls on the
  previously-created session.
- **Worker/API share**: Celery `analyze_data_task` and the API both operate on
  the same shared-data file successfully.

**Integration point documented**: in-memory `session_registry` is rebuilt
lazily from DB state via `_refresh_live_session()`; the DB is the source of
truth for metadata/history, the registry for live objects.

---

## Test 6 — Error propagation across services

**Scenario** (`TestErrorPropagation`)

- Unknown specialist → orchestrator `ValueError` → API `400` with
  `"analyze failed: ..."` detail **and** a persisted `failed` task row whose
  `error` field records the exception.
- Auth/validation failures propagate as structured errors: unauthenticated
  `401`, invalid payload `422` (`{"errors": ...}`), wrong password `401`.
- Worker error handling: `analyze_data_task` with a bogus specialist returns
  `{"status": "error", "error": ...}` instead of raising (matches Celery
  task contract).
- Authorization boundaries: unknown session `404`, cross-user access `403`.

**Note preserved**: path-traversal payloads (`../escape.csv`) are rejected at
validation with `422` before reaching any agent.

---

## Test 7 — Logging across services

**Scenario** (`TestLoggingAcrossServices`)

- `RequestLoggingMiddleware` logs `GET /health -> 200 (… ms)` and sets the
  `X-Process-Time-Ms` header on responses.
- Failed execution logs at ERROR level (`Session <id> analyze failed`) via the
  `_handle_execution_error` path — asserted through `caplog`.
- Compose files verified: dev stack mounts `api-logs`/`worker-logs` volumes;
  prod stack centralizes on `json-file` with `max-size: 10m` / `max-file: 3`
  rotation; the middleware is wired inside `create_app`.

---

## Test 8 — Monitoring and metrics

**Scenario** (`TestMonitoringAndMetrics`)

- Both health endpoints live: FastAPI `/health` (`status: ok`) and Flask
  `/health` (`status: healthy`) — the Flask one is the Compose healthcheck
  probe.
- Celery config assertions: `task_track_started`, 1 h hard / 55 min soft
  limits.
- `docker/prometheus.yml` scrapes `openscience-api` (with
  `metrics_path: /metrics`), `postgresql`, `redis`.
- Compose healthchecks exist for `api`, `ui`, `worker`, `db`, `redis`;
  `flower`'s liveness is bound to its `depends_on: [redis, worker]` chain.

---

## Test 9 — Backup and recovery

**Scenario** (`TestBackupAndRecovery`)

- Seeds a user + session through the ORM, backs up the database with the
  SQLite online-backup API, repoints the engine at the restored file and
  verifies rows survive (`SELECT username`, `SELECT name FROM sessions`).
- Runs the `backup_manager` agent for real: snapshots a project directory to
  `backup_root/snapshot-<UTC>` via `snapshot()` and asserts files land on
  disk.
- Verifies the `data_management` category retains `data_ingestor`,
  `backup_manager`, `version_controller`, and that a backup-style task routes
  to a valid agent.

**Bugs found & fixed (skill-dispatch layer)**

| Bug | Fix |
|---|---|
| `skill_run` forwarded orchestration metadata (`context`, empty `parameters`) into skill ops — `snapshot() got an unexpected keyword argument 'context'` (and, after a naive fix, `missing required positional arguments`). | `skill_run` now drops kwargs the target op doesn't accept (unless it takes `**kwargs`); the test passes explicit `{source_dir, backup_root}` matching the real `snapshot()` contract. |
| `_common.unwrap` (first iteration) stripped `context` unconditionally, breaking writing skills that legitimately accept it. | Reverted: reserved-key filtering is limited to `("operation", "parameters")`; signature-aware filtering lives in `skill_run`. |

---

## Test 10 — Upgrade path (Alembic)

**Scenario** (`TestUpgradePath`)

- `alembic upgrade head` against a fresh SQLite DB creates
  `users/agents/sessions/tasks/alembic_version` with the expected
  `sessions` columns.
- `downgrade base` removes them; re-upgrade restores the schema — full
  roundtrip verified with `sqlalchemy.inspect`.
- ORM metadata (`Base.metadata.tables`) matches the `0001` migration tables,
  so the runtime models and migration history stay in sync.

---

## Fixes applied to production code during this experiment

| File | Change |
|---|---|
| `src/openscience/core/sandbox.py` | Best-effort `setrlimit` — no longer crashes on platforms where hard limits are `RLIM_INFINITY` (macOS dev). |
| `src/openscience/skills/writing/scientific_writing.py` | `_write_methods` unwraps framework `Result` objects before reading structured keys. |
| `src/openscience/skills/visualization/matplotlib_skill.py` | `render` accepts `viz_type="auto"` via a new `_auto` builder and unwraps `Result`/nested `{"data": ...}` envelopes. |
| `src/openscience/skills/_common.py` | `skill_run` filters kwargs by the target op's signature (drops orchestration noise like `context`); `unwrap` keeps `context` for ops that declare it. |

## Cross-cutting integration points (reference)

- **Agent registry**: `AgentOrchestrator.agents` ⇄ `AgentModel` rows,
  synced at API startup via `register_agents()` in `openscience/api/deps.py`.
- **Session state**: live `ScienceSession` objects in `session_registry`
  ⇄ `sessions`/`tasks` tables; registry rebuilt lazily after restart.
- **Auth**: `OPENSCIENCE_API_*`-configured settings (`rate_limit_enabled`
  off in tests), JWT via `auth.py` middleware on all `/api/v1/*` routes.
- **Validation**: `SafeFilePath` rejects absolute paths and `..` — tests use
  cwd-relative fixture files (a `monkeypatch.chdir(tmp_path)` fixture).
- **Workers**: `openscience.workers.tasks.celery_app` (eager-run in tests;
  Redis broker in Docker) shares the `ScienceSession` pipeline with the API.
- **Observability**: request logging middleware + Compose healthchecks +
  Prometheus scrape jobs for api/postgres/redis, Flower for tasks.

## How to run

```bash
# Integration suite only (Docker test skips gracefully without a daemon)
.venv/bin/python -m pytest tests/integration/test_integration.py -v

# Entire repo suite
.venv/bin/python -m pytest tests/ -q
```
