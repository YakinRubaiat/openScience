# Experiment 02 — REST API Integration Tests

**Date**: 2026-11-22
**Subject**: openScience REST API (`openscience.api.main`)
**Server**: `uvicorn openscience.api.main:app --host 127.0.0.1 --port 8001`
**Auth flow**: Register → Login (JWT Bearer) → Authenticated requests
**Methodology**: All requests executed with `curl` against a live `uvicorn` instance backed by a fresh SQLite database. Each request and raw response body + HTTP status is captured below. Status codes verified against expected values.

---

## Environment

| Component | Value |
|---|---|
| Server binary | `.venv/bin/uvicorn openscience.api.main:app` |
| Host / Port | `127.0.0.1:8001` |
| Database | `sqlite:///<repo>/openscience.db` (freshly created) |
| API prefix | `/api/v1` |
| Rate limit (per settings) | `60/minute`, enabled |
| Auth | JWT Bearer, HS256, 60 min expiry |
| OpenAPI | `/openapi.json` (auto-generated) |
| Docs UI | `/docs` (Swagger), `/redoc` (ReDoc) |

A setup script registers a dedicated user (`testuser` / `test@example.com`) and
obtains a bearer token used by all authenticated calls.

> **Setup requiremeent**: `email-validator` had to be added to the venv
> (`pip install email-validator`) because `pydantic-settings` requires it for
> `EmailStr` fields used by the auth schema. This is **not** listed in
> `pyproject.toml`'s runtime deps — see *Issues Found* below.

---

## Summary Table

| # | Test | Endpoint(s) | Result |
|---|---|---|---|
| 1 | API server startup & docs | `GET /health`, `GET /docs`, `GET /openapi.json` | ✅ PASS |
| 2 | `GET /api/v1/agents` | w/o auth → 401, with auth → 200 (111 agents) | ✅ PASS |
| 3 | `GET /api/v1/agents/{name}` | found → 200, missing → 404, no auth → 401 | ✅ PASS |
| 4 | `POST /api/v1/sessions` | valid → 201, no auth → 401, bad body → 422 | ✅ PASS |
| 5 | `POST /api/v1/sessions/{id}/load` | valid → 200, missing session → 404, missing file → ⚠ 200 (see Issues) | ⚠ PARTIAL |
| 6 | `POST /api/v1/sessions/{id}/analyze` | valid → 200 with structured result | ✅ PASS |
| 7 | `POST /api/v1/sessions/{id}/visualize` | valid → 200, unknown key → 404, no results → 400 | ✅ PASS |
| 8 | Auth endpoints (register/login/me) | happy paths + 401/403/409/422 paths | ✅ PASS |
| 9 | Error handling (404 / 405 / 422 / 403) | all return correct codes + JSON envelopes | ✅ PASS |
| 10 | Rate limiting (60/min) | first 60 → 200, next 10 → 429 with `Rate limit exceeded` body | ✅ PASS |

**Overall**: 9 / 10 fully passing. Test 5 (load) passes for status codes but reveals a
framework-level gap (no missing-file validation in `data_ingestor`); documented in
*Issues Found* and *Recommendations*.

---

## Test 1 — API Server Startup

**Goal**: Verify uvicorn boots, the health route works, and OpenAPI/docs are reachable.

```
$ curl -sS http://127.0.0.1:8001/health
{"status":"ok","version":"0.1.0"}
HTTP: 200

$ curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/docs
200

$ curl -sS http://127.0.0.1:8001/openapi.json | jq '.info, (.paths | keys)'
{
  "title": "openScience API",
  "version": "0.1.0"
}
Paths exposed:
  /api/v1/agents
  /api/v1/agents/{name}
  /api/v1/analysis/capabilities
  /api/v1/auth/login
  /api/v1/auth/me
  /api/v1/auth/register
  /api/v1/sessions
  /api/v1/sessions/{session_id}
  /api/v1/sessions/{session_id}/analyze
  /api/v1/sessions/{session_id}/load
  /api/v1/sessions/{session_id}/results
  /api/v1/sessions/{session_id}/visualize
  /api/v1/sessions/{session_id}/write
  /health
```

**Status**: ✅ `200 OK`, OpenAPI matches `main.py`'s registered routers.

---

## Test 2 — `GET /api/v1/agents`

**Goal**: Verify the agents list endpoint requires auth and returns the registered agents.

Without auth:

```
$ curl -sS http://127.0.0.1:8001/api/v1/agents
HTTP: 401
{"detail":"Not authenticated","error":"HTTPException"}
```

With auth (`Authorization: Bearer $TOKEN`):

```
HTTP: 200
{"agents":[...111 entries...],"total":111}
```

Sample entries returned:

```json
{"name":"qc_analyzer","category":"analysis","description":"Quality control metrics",
 "required_skills":["scanpy","seurat","multiqc"],
 "input_types":["anndata","seurat_object","fastq"],
 "output_types":["qc_report","qc_plots","filtered_data"]}
{"name":"deseq2_specialist","category":"analysis","description":"Bulk RNA-seq differential expression", ...}
{"name":"publication_formatter","category":"visualization", ...}
{"name":"methods_writer","category":"writing", ...}
```

**Validation**:
- 111 agents returned, grouped by category (`analysis`, `data_management`, `experiment`,
  `literature`, `review`, `visualization`, `writing`).
- Response conforms to `AgentListResponse { agents: AgentDetail[], total: int }`.
- Unauthenticated calls correctly rejected with **401**.

**Status**: ✅ PASS

---

## Test 3 — `GET /api/v1/agents/{name}`

**Goal**: Fetch a single agent by name; verify 404 for unknown names and 401 without auth.

Found:

```
$ curl -sS http://127.0.0.1:8001/api/v1/agents/qc_analyzer -H "Authorization: Bearer $TOKEN"
HTTP: 200
{"name":"qc_analyzer","category":"analysis","description":"Quality control metrics", ...}
```

Not found:

```
$ curl -sS http://127.0.0.1:8001/api/v1/agents/does_not_exist -H "Authorization: Bearer $TOKEN"
HTTP: 404
{"detail":"Unknown agent: does_not_exist","error":"HTTPException"}
```

Unauthenticated:

```
$ curl -sS http://127.0.0.1:8001/api/v1/agents/qc_analyzer
HTTP: 401
{"detail":"Not authenticated","error":"HTTPException"}
```

**Status**: ✅ PASS — all three code paths correct.

---

## Test 4 — `POST /api/v1/sessions`

**Goal**: Create sessions; verify shape of `SessionResponse` and 401/422 paths.

Happy path:

```
$ curl -sS -X POST http://127.0.0.1:8001/api/v1/sessions \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"name":"integration-test-session","project_dir":"/tmp/openscience-test-proj","compute_backend":"local"}'
HTTP: 201
{
  "id": "c8665a0c-e7f4-4757-adfb-66aacf5e0fab",
  "name": "integration-test-session",
  "owner_id": "77a634f3-1147-4907-bae7-0a05860e79bd",
  "project_dir": "/tmp/openscience-test-proj",
  "compute_backend": "local",
  "status": "active",
  "data_keys": [],
  "created_at": "2026-11-22T19:43:07.746603",
  "updated_at": "2026-11-22T19:43:07.746608"
}
```

No auth → `401 {"detail":"Not authenticated", ...}`
Missing `name` → `422 {"detail":"Request validation failed","errors":[{"type":"missing","loc":["body","name"], ...}]}`

**Validation**:
- Response model `SessionResponse` matches the OpenAPI schema (UUID id, owner_id, status, etc.).
- Two sessions created successfully in this run; both listable later via `GET /sessions/{id}`.

**Status**: ✅ PASS

---

## Test 5 — `POST /api/v1/sessions/{id}/load`

**Goal**: Load a CSV into a session; verify the task record and `data_keys` update. Probe error paths.

Setup:

```
$ cat > /tmp/openscience-test-proj/data.csv <<EOF
gene,cell1,cell2,cell3
GAPDH,100,200,150
ACTB,120,210,180
MALAT1,500,600,550
EOF
```

Happy path:

```
$ curl -sS -X POST http://127.0.0.1:8001/api/v1/sessions/$SESSION_ID/load \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"file_path":"/tmp/openscience-test-proj/data.csv","format":"csv","name":"expression"}'
HTTP: 200
{"id":"2b4c7fa1-...","task_type":"load","status":"completed",
 "result":{"loaded":"expression","data_keys":["expression"]}}
```

Unknown session:

```
HTTP: 404
{"detail":"Session not found: 00000000-...-0000","error":"HTTPException"}
```

**Missing file (potential bug)**:

```
$ curl -sS -X POST http://127.0.0.1:8001/api/v1/sessions/$SESSION_ID/load \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"file_path":"/tmp/does-not-exist.csv","format":"csv"}'
HTTP: 200   ← expected 400 / 422
{"task_type":"load","status":"completed",
 "result":{"loaded":"/tmp/does-not-exist.csv","data_keys":["expression","does-not-exist"]}}
```

> ⚠ The framework `data_ingestor` agent does not check `Path(...).exists()` before
> "succeeding". The session ends up with a phantom data key (`does-not-exist`). The
> row in `_data` holds a `Result` blob rather than loaded data, so subsequent
> analysis simply consumes the empty blob. See *Issues Found*.

**Status**: ⚠ PARTIAL — endpoint code/HTTP semantics are correct, but the underlying
agent silently accepts nonexistent files.

---

## Test 6 — `POST /api/v1/sessions/{id}/analyze`

**Goal**: Run an analysis over previously-loaded data.

```
$ curl -sS -X POST http://127.0.0.1:8001/api/v1/sessions/$SESSION_ID/analyze \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{
      "task": "compute basic QC metrics",
      "specialist": "qc_analyzer",
      "data_name": "expression",
      "parameters": {"min_genes": 10}
    }'
HTTP: 200
{
  "id":"11fd4784-...",
  "task_type":"analyze",
  "status":"completed",
  "result":{
    "data":{"skill":"scanpy","operation":"qc_analysis","status":"ok","data":{...}},
    "metadata":{"agent":"qc_analyzer"},
    "artifacts":[]
  }
}
```

**Validation**:
- Endpoint returns the `TaskResponse` schema.
- Result body has the standard `{data, metadata, artifacts}` Result shape.

**Status**: ✅ PASS

---

## Test 7 — `POST /api/v1/sessions/{id}/visualize`

**Goal**: Generate a visualization from the latest analysis result.

Happy path (against the result produced in Test 6):

```
$ curl -sS -X POST http://127.0.0.1:8001/api/v1/sessions/$SESSION_ID/visualize \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"type":"auto","style":"publication"}'
HTTP: 200
{
  "task_type":"visualize",
  "status":"completed",
  "result":{
    "data":{
      "figure":{"skill":"matplotlib","operation":"render","status":"ok", ...},
      "viz_type":"auto","style":"publication"
    },
    "metadata":{"agent":"publication_formatter"}
  }
}
```

Unknown result key:

```
$ curl -sS -X POST http://127.0.0.1:8001/api/v1/sessions/$SESSION_ID/visualize \
    -d '{"result_key":"no_such_result"}' ...
HTTP: 404
{"detail":"Result not found: no_such_result","error":"HTTPException"}
```

Empty session (no results) — tested against a brand-new `truly-empty` session:

```
HTTP: 400
{"detail":"No analysis results available yet","error":"HTTPException"}
```

**Status**: ✅ PASS — all three branches (`200`, `404`, `400`) behave as documented.

---

## Test 8 — Authentication endpoints

Endpoints covered: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`.

| Sub-test | Request | Response |
|---|---|---|
| 8a. Register new user | `POST /register {username:bob2026,email:bob2026@example.com,password:bob_password_1}` | `201`, returns `UserResponse {id, username, email, is_active:true, is_admin:false, created_at}` |
| 8b. Register duplicate | Same as 8a | `409 {"detail":"Username or email already registered"}` |
| 8c. Invalid email | `{email:"not-an-email", ...}` | `422` — pydantic `value_error` |
| 8d. Short password | `{password:"short", ...}` | `422` — `string_too_short` (min 8) |
| 8e. Valid login | `POST /login {username:bob2026, password:bob_password_1}` | `200 {"access_token":"…","token_type":"bearer","expires_in":3600}` |
| 8f. Wrong password | Same username, `password:"wrong"` | `401 {"detail":"Incorrect username or password"}` |
| 8g. Unknown user | `username:"ghost"` | `401 {"detail":"Incorrect username or password"}` |
| 8h. `/me` with valid token | `Authorization: Bearer $TOKEN` | `200 {"id":"…","username":"bob2026", …}` |
| 8i. `/me` with forged token | `Authorization: Bearer bad.token.here` | `401 {"detail":"Could not validate credentials"}` |
| 8j. `/me` no header | (none) | `401 {"detail":"Not authenticated"}` |

**Observations**:
- Token lifetime is `3600 s` (60 min) and `token_type == "bearer"`. Matches `APISettings.access_token_expire_minutes = 60`.
- JWT decodes with `sub`, `exp`, `iat`, `type:"access"`.
- The duplicate-username check correctly returns **409 Conflict**, validating the `or_(username, email)` filter in `auth.py`.

**Status**: ✅ PASS

---

## Test 9 — Error Handling (404, 405, 422, 403, 500)

| Sub-test | Request | Status | Body |
|---|---|---|---|
| 9a. Unknown path | `GET /api/v1/not_a_route` | **404** | `{"detail":"Not Found"}` |
| 9b. Unknown agent | `GET /api/v1/agents/no_such_agent` | **404** | `{"detail":"Unknown agent: no_such_agent","error":"HTTPException"}` |
| 9c. Unknown session | `GET /api/v1/sessions/00000000-...-0000` | **404** | `{"detail":"Session not found: …","error":"HTTPException"}` |
| 9d. Wrong method | `DELETE /api/v1/agents/qc_analyzer` | **405** | `{"detail":"Method Not Allowed"}` |
| 9e. Invalid JSON | `POST /auth/login` body=`not json` | **422** | `{"detail":"Request validation failed","errors":[{"type":"json_invalid", ...}]}` |
| 9f. Missing field | `POST /sessions` `{}` | **422** | `{"detail":"Request validation failed","errors":[{"type":"missing","loc":["body","name"], ...}]}` |
| 9g. Cross-user access | Bob reads testuser's session | **403** | `{"detail":"Not authorized to access this session","error":"HTTPException"}` |

**500-handling**: The catch-all `@app.exception_handler(Exception)` returns
`{"detail":"Internal server error"}` with 500 — verified by code inspection
(`main.py:82-88`). No live 500 was triggered during testing because all endpoint
failures are handled upstream (notably `_handle_execution_error` → 400 for analyze/
load failures). Rate limiting's unhandled `RateLimitExceeded` is wired separately
through `_rate_limit_exceeded_handler`.

**Status**: ✅ PASS

---

## Test 10 — Rate Limiting

**Setting**: `rate_limit = "60/minute"` (config.py). `Limiter` from `slowapi` is wired
with `get_remote_address` as the key function and applied via `SlowAPIMiddleware`.

Test plan: burst 70 sequential requests to `/health` and tally codes.

```
$ for i in $(seq 1 70); do curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/health; done
... 200 × 60, then 429 × 10

First few / last few codes: 1:200 2:200 3:200 68:429 69:429 70:429
200s: 60 | 429s: 10 | other: 0
```

Response body when limited:

```
HTTP: 429
{"error":"Rate limit exceeded: 60 per 1 minute"}
```

After waiting ~65 s (a sliding-window reset), the next request again returns `200`.

**Validation**:
- The limiter correctly enforces the **60 req/min/IP** policy.
- The 429 body comes from slowapi's `_rate_limit_exceeded_handler` and is plain JSON.
- Rate limit applies **even to `/health`**, which is expected since `SlowAPIMiddleware`
  wraps all routes. If a future change exempts `/health` from limiting, consider
  configuring `Limiter(default_limits=...)` per-route instead of globally.

**Status**: ✅ PASS

---

## Issues Found

### I1 — `email-validator` is not a declared dependency
- **Symptom**: `from openscience.api.main import app` crashes with
  `ImportError: email-validator is not installed` whenever pydantic attempts to
  resolve the `EmailStr` field on `UserCreateRequest`.
- **Where**: `pyproject.toml`'s `[project.dependencies]` does not list `email-validator`
  or `pydantic[email]`.
- **Fix**: add `pydantic[email]` (or `email-validator`) to the runtime deps — one-line
  edit in `pyproject.toml`. Until then the API server cannot start from a clean venv.
- **Severity**: blocking on fresh installs; mitigated locally by `pip install email-validator`.

### I2 — `data_ingestor` silently succeeds on missing files (Test 5b)
- **Symptom**: `POST /sessions/{id}/load` with `file_path=/tmp/does-not-exist.csv`
  returns `200 OK` and adds the (nonexistent) filename as a data key.
- **Where**: `openscience/agents/data_management/data_ingestor.py::execute` calls
  `self.orchestrator.execute_skill(...)` without first `Path(file_path).exists()`.
  The scanned skill never raises; the `Result` returned embeds the path metadata
  rather than loaded data.
- **Fix suggestion**: in `DataIngestor.execute`, add a guard:
  ```python
  if file_path and not Path(str(file_path)).exists():
      raise FileNotFoundError(f"Input file does not exist: {file_path}")
  ```
  The route's existing `_handle_execution_error` will then map this to a proper
  `400 Bad Request`.
- **Severity**: medium — corrupts `session.data_keys` and lets callers think data
  loaded successfully.

### I3 — `/health` is rate-limited
- **Symptom**: the liveness probe is throttled at 60 req/min/IP.
- **Where**: `main.py` applies `SlowAPIMiddleware` globally; `health()` is not exempted.
- **Severity**: low — fine for manual probes, but Kubernetes/Docker healthchecks that
  hit /health every few seconds from the kubelet IP could intermittently 429.
  Mitigation: pass `exempt` decorator to health or use a separate limiter just for
  routers. Not a correctness bug.

### I4 — No automated integration coverage beyond unit-style tests
- Existing `tests/api/test_*.py` exercise endpoint functions in-process via
  FastAPI's `TestClient`. They do not run a live uvicorn instance and therefore
  never test `SlowAPIMiddleware`, request logging, or real TCP/TLS behavior. This
  experiment fills that gap.

---

## Fixes Applied During This Run

- Added `email-validator` to the local venv so the API server could start
  (`pip install email-validator`). **Not committed** — recommend codifying in
  `pyproject.toml` per I1 above.
- Created fresh `openscience.db` for the run so prior test state didn't contaminate
  counts (`alice`/`testuser` already in the DB were created earlier in the session).

---

## Recommendations

1. Add `pydantic[email]` to `pyproject.toml`'s `[project.dependencies]`.
2. Add file-existence validation in `data_ingestor.py` before delegating to a skill.
3. Exempt `/health` from slowapi rate limiting, or use a much higher budget for that
   route specifically.
4. Wire this experiment as a CI job: spin up uvicorn against a tmp sqlite DB, run
   the curl batch above, diff against the status codes documented here.
5. Consider a small live-server smoke test (e.g., using `pytest-xdist` +
   `uvicorn.Server` in a fixture) so future regressions hit an actual socket.

---

## Appendix — Reproduction Script

```bash
#!/usr/bin/env bash
set -e
cd /Users/srubaiat/openScience
.venv/bin/pip install -q email-validator
rm -f openscience.db
.venv/bin/uvicorn openscience.api.main:app --host 127.0.0.1 --port 8001 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT
sleep 4
BASE=http://127.0.0.1:8001

# Auth bootstrap
curl -sS -X POST $BASE/api/v1/auth/register -H 'Content-Type: application/json' \
  -d '{"username":"testuser","email":"test@example.com","password":"testpassword123"}' > /dev/null
TOKEN=$(curl -sS -X POST $BASE/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"testuser","password":"testpassword123"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')
AUTH="Authorization: Bearer $TOKEN"

# 1. Health
curl -sS $BASE/health
# 2. Agents
curl -sS $BASE/api/v1/agents -H "$AUTH"
# 3. One agent
curl -sS $BASE/api/v1/agents/qc_analyzer -H "$AUTH"
# 4. Create session
SID=$(curl -sS -X POST $BASE/api/v1/sessions -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"integration-test"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')
# 5. Load
echo 'gene,cell1,cell2
GAPDH,100,200' > /tmp/x.csv
curl -sS -X POST $BASE/api/v1/sessions/$SID/load -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"file_path":"/tmp/x.csv","format":"csv","name":"expression"}'
# 6. Analyze
curl -sS -X POST $BASE/api/v1/sessions/$SID/analyze -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"task":"qc","specialist":"qc_analyzer","data_name":"expression","parameters":{}}'
# 7. Visualize
curl -sS -X POST $BASE/api/v1/sessions/$SID/visualize -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"type":"auto","style":"publication"}'
# 8. /me
curl -sS $BASE/api/v1/auth/me -H "$AUTH"
# 9. 404
curl -sS $BASE/api/v1/not_a_route -H "$AUTH"
# 10. Rate limit — burst 70
for i in $(seq 1 70); do curl -sS -o /dev/null -w "$i:%{http_code}\n" $BASE/health; done
```
