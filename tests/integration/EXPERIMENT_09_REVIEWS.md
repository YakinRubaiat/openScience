# Experiment 09 — Comprehensive Review Agent Test Suite

**Date**: 2026-11-22
**Target**: openScience @ `/Users/srubaiat/openScience`
**Scope**: All 10 review agents executed against the codebase (154 Python source files, ~5,522 LOC, 111 cataloged agents)
**Method**: Each review agent's documented skills were executed with real tools where available (bandit 1.9.x, ruff, coverage.xml analysis, manual OWASP/WCAG/REST audits), findings recorded, prioritized (P0 = critical, P1 = high, P2 = medium, P3 = low), and critical issues fixed in place.

---

## Executive Summary

| # | Review Agent | Scope | Findings | P0 | P1 | P2 | P3 | Fixed |
|---|--------------|-------|----------|----|----|----|----|-------|
| 1 | security_reviewer | Full codebase | 9 | 1 | 3 | 3 | 2 | 1 |
| 2 | code_quality_reviewer | Core modules | 8 | 0 | 2 | 3 | 3 | 0 |
| 3 | architecture_reviewer | System design | 7 | 0 | 3 | 2 | 2 | 0 |
| 4 | performance_reviewer | API endpoints | 6 | 0 | 2 | 3 | 1 | 0 |
| 5 | documentation_reviewer | All docs | 5 | 0 | 1 | 2 | 2 | 0 |
| 6 | test_coverage_reviewer | Test suite | 7 | 1 | 3 | 2 | 1 | 0 |
| 7 | database_reviewer | Models & queries | 6 | 0 | 2 | 3 | 1 | 0 |
| 8 | api_design_reviewer | OpenAPI spec | 7 | 0 | 2 | 3 | 2 | 0 |
| 9 | accessibility_reviewer | UI | 8 | 0 | 2 | 4 | 2 | 0 |
| 10 | devops_reviewer | Docker & CI/CD | 8 | 1 | 2 | 3 | 2 | 0 |
| | **TOTAL** | | **71** | **3** | **22** | **28** | **18** | **1** |

**P0 issues fixed during this run**: 1 of 3 (Flask debug mode). The other two P0s require design decisions, documented with recommended patches below.

---

## Test 1 — security_reviewer (full codebase)

**Skills executed**: bandit (`bandit -r src/`), manual OWASP Top 10 audit, secrets scan, dependency review of `pyproject.toml`.

### Findings

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| SEC-01 | **P0** | Flask dev server hardcoded `debug=True` — Werkzeug debugger allows arbitrary code execution (Bandit B201, CWE-94) | `src/openscience/server.py:214` |
| SEC-02 | **P1** | XSS via `innerHTML` template injection — agent names/descriptions interpolated unsanitized into DOM | `src/openscience/server.py:178,187,202` |
| SEC-03 | **P1** | Default JWT `secret_key` shipped in source (`openscience-dev-secret-key-change-in-production`); silently used if env var unset | `src/openscience/api/config.py:32` |
| SEC-04 | **P1** | Path traversal risk: `/sessions/{id}/load` accepts arbitrary `file_path`, passed to `Path()` without sandbox prefix validation | `api/routes/sessions.py:161`, `core/session.py:77` |
| SEC-05 | **P2** | Pickle deserialization for session persistence (Bandit B301/B403, CWE-502) | `src/openscience/core/session.py:245` |
| SEC-06 | **P2** | CORS wildcard `cors_origins=["*"]` combined with `cors_allow_credentials=True` — invalid and dangerous combination | `api/config.py:39-40` |
| SEC-07 | **P2** | Hardcoded DB credentials in compose (`openscience:openscience`) | `docker-compose.yml:12,68,97-98` |
| SEC-08 | **P3** | Two `try/except: continue` blocks in plugin loader can mask security-relevant import errors (Bandit B112) | `core/orchestrator.py:281,289` |
| SEC-09 | **P3** | Approval-broker default falls back to interactive `input()` — unusable and a confused-deputy risk in API contexts | `core/sandbox.py:126` |

### Prioritized recommendations

1. **SEC-01 → FIXED this run.** `server.py` now requires explicit `FLASK_DEBUG` env opt-in; bandit re-scan confirms B201 eliminated.
2. **SEC-03**: Fail-fast at startup when `secret_key` equals the dev default and `debug=False`; rely on pydantic `Field(..., env=...)` with no default in prod profile.
3. **SEC-02**: Replace `innerHTML +=` with `document.createElement`/`textContent`, or escape via a small `escapeHtml()` helper.
4. **SEC-04**: Resolve `Path(file_path).resolve()` and enforce it lives under `session.project_dir`; reject `..` segments.
5. **SEC-06**: When credentials allowed, enumerate explicit origins; otherwise drop `cors_allow_credentials`.
6. **SEC-05/07**: Move persistence from pickle to JSON/SQLite; move compose secrets to `.env` (already gitignored) with `${VAR:?required}` guards.

---

## Test 2 — code_quality_reviewer (core modules)

**Skills executed**: ruff (`ruff check src/`), black availability check, complexity review of `core/`, naming/idiom audit.

### Findings

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| CQ-01 | P1 | 22 ruff violations in tree, incl. 1 real bug class: **F821 undefined name** | `ruff check src/`: 12×UP006, 4×I001, 2×F841, **1×F821**, 1×F401, 1×RUF022, 1×RUF100 |
| CQ-02 | P1 | mypy configured `strict = true` but no evidence the tree passes; `api/models` use `# noqa: F821` forward-ref hacks that strict mypy will flag | `pyproject.toml:101-103`, `models/user.py:33` |
| CQ-03 | P2 | `_run_awaitable()` spawns a thread + fresh event loop per call when a loop is running — fragile sync/async boundary, deadlock-prone under Flask worker pools | `core/sandbox.py:175-208` |
| CQ-04 | P2 | Broad `except Exception: continue` in agent loader silently skips broken agents — failures invisible at runtime | `core/orchestrator.py:280-290` |
| CQ-05 | P2 | Keyword-map routing is case-sensitive substring matching on unvalidated input; no tests exercise the fallback chain | `core/orchestrator.py:229-259` |
| CQ-06 | P3 | Private-member access across layers: API routes read `live._data`, `live._results` | `api/routes/sessions.py:172,182,341` |
| CQ-07 | P3 | `Result.coerce()` is 25 lines of nested dict-sniffing — a candidate for pydantic model validation | `core/orchestrator.py:29-53` |
| CQ-08 | P3 | Ruff baseline ignores 9 rule classes wholesale (B008, BLE001, S112, N999, ...) rather than per-file | `pyproject.toml:86-96` |

### Recommendations

1. Fix F821 immediately (it is a runtime `NameError` waiting); run `ruff check --fix` for the 17 auto-fixables.
2. Replace `_run_awaitable` with `anyio.from_thread`/`asgiref.sync.async_to_sync`, or make orchestrator async end-to-end.
3. Log skipped agent imports at WARNING with the exception; add a `--strict-agents` CLI flag that raises.
4. Expose `ScienceSession.data_keys` / `.result_keys` public properties; delete `_`-access from API layer.
5. Tighten ruff ignores per-file instead of globally; burn down the baseline.

---

## Test 3 — architecture_reviewer (system design)

**Skills executed**: dependency-graph walk (manual, via imports), layering audit, pattern review against the README's published architecture diagram.

### Findings

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| AR-01 | P1 | **Two parallel web stacks**: Flask (`server.py` + global `ScienceSession`) and FastAPI (`api/main.py`) expose overlapping `/api/*` surfaces with different auth models (none vs JWT). README documents one architecture; code ships two | `server.py:20-74` vs `api/main.py` |
| AR-02 | P1 | Stated layers "Skill Registry / Connector Framework / Compute Backend Router" from README diagram have **no corresponding packages** for connectors (empty `security/` dir; connectors dir exists but routing layer absent) | README:82-93 vs `src/openscience/` |
| AR-03 | P1 | `session_registry` is an in-process global — breaks under >1 uvicorn worker and makes sessions non-shareable between `api` and `worker` containers | `api/deps.py`, used in `routes/sessions.py` |
| AR-04 | P2 | Circular-import risk managed by function-level imports (`server.py:13`, `database.py:54`) rather than dependency inversion | multiple |
| AR-05 | P2 | `AgentOrchestrator` doubles as skill executor (`execute_skill` returns stub dicts) — violates SRP; real tool binding is subclass-only, undocumented extension point | `core/orchestrator.py:164-185` |
| AR-06 | P3 | `Sandbox` enforcement is advisory: only wraps `agent.execute`; file/network access inside agents is unconstrained (no seccomp/network namespace) despite "OS-Level Sandbox" claim | `core/sandbox.py`, README:88-89 |
| AR-07 | P3 | Versioning: API is `/api/v1` but no deprecation policy or schema-version field on `Task`/`Result` | `api/config.py:27` |

### Recommendations

1. **Pick one web stack.** Keep FastAPI (auth, models, migrations already exist), port Flask's two remaining endpoints, delete `server.py` or reduce it to a static-UI server.
2. Add ADRs in `docs/architecture/` recording: single-stack decision, session-store backend (Redis), and sandbox threat model.
3. Move `session_registry` behind Redis (already in compose) keyed by session id, with pickle→JSON serialization (also fixes SEC-05).
4. Introduce `SkillProvider` protocol + entry-points registry so real tools bind without subclassing the orchestrator.
5. Either implement real OS isolation (bubblewrap/firejail/container-per-task) or downgrade README claims to "policy-level sandbox."

---

## Test 4 — performance_reviewer (API endpoints)

**Skills executed**: static hot-path analysis of route handlers, N+1 scan, serialization cost review (no load harness run — endpoints not externally reachable in this environment).

### Findings

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| PF-01 | P1 | `POST /sessions/{id}/analyze` executes the full agent pipeline **synchronously in the request cycle** — long analyses will exceed proxy timeouts and block a worker | `routes/sessions.py:198-230` |
| PF-02 | P1 | `GET /sessions/{id}/results` re-serializes **all** live results plus full task history per call — unbounded payload growth; no pagination | `routes/sessions.py:318-353` |
| PF-03 | P2 | Agent module discovery (`_load_agents`) walks and imports **every agent module at orchestrator init** — slow cold start, imports heavy exotic deps eagerly | `core/orchestrator.py:268-303` |
| PF-04 | P2 | `list_agents` (Flask) and startup `register_agents` hit the DB/ORM once per agent with no bulk upsert | `api/deps.py`, `server.py:25-37` |
| PF-05 | P2 | Rate limit keyed on `get_remote_address` — all pods behind one ingress IP share a bucket without `X-Forwarded-For` handling | `api/main.py:44` |
| PF-06 | P3 | Serialization helper `to_jsonable` deep-walks arbitrary result objects per task write; numpy arrays/pandas frames hit slow python paths | `api/utils/serialization.py` |

### Recommendations

1. Move analyze/visualize/write to the Celery worker fleet (compose already ships `worker` + Flower) and return `202 Accepted` + task id; add `GET /tasks/{id}` polling.
2. Paginate `/results` (`limit`/`offset`, or cursor on `created_at`) and add a `fields=` filter.
3. Lazy-load agent modules: registry of import paths, import on first use.
4. Honor `ProxyHeadersMiddleware`/`X-Forwarded-For` for slowapi keying behind ingress.
5. Benchmark `to_jsonable` on typical `anndata`-sized results; short-circuit common scientific types.

---

## Test 5 — documentation_reviewer (all docs)

**Skills executed**: docs-tree completeness audit vs code reality, docstring coverage spot-check, link/accuracy verification.

### Findings

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| DOC-01 | P1 | `docs/agents.md` claims **111 agents** with detailed skills/IO — only review-category agents have any implementation evidence; cataloged skills (`pubmed_api`, `DESeq2`, ...) are not in the tree or `pyproject` deps. Aspirational docs presented as fact | `docs/agents.md` vs `src/openscience/agents/` |
| DOC-02 | P2 | README architecture diagram advertises nonexistent layers (Connector Framework, Compute Backend Router, OS-Level Sandbox) | README:61-94, see AR-02/AR-06 |
| DOC-03 | P2 | `docs/api.md` not verifiable against live OpenAPI: routes exist for auth/agents/sessions/analysis; no doc coverage of request/response schemas drift policy | `docs/api.md` |
| DOC-04 | P3 | Docstring coverage uneven: `core/` well documented; `api/models/*` and `api/utils/*` largely one-liners; no docstring-coverage gate in CI | spot check |
| DOC-05 | P3 | Good bones: 13 docs pages, mkdocs configured, getting-started/docker/security present; changelog exists | `docs/`, `mkdocs.yml` |

### Recommendations

1. Mark every unimplemented agent row in `agents.md` with a **Status: planned** column, or generate the catalog from the actual registry at build time.
2. Add an "Implementation status" section to README distinguishing shipped vs roadmap features.
3. Add `interrogate` (docstring coverage) as a non-blocking CI report with a ratchet file.
4. Add a CI check that `/openapi.json` diffs cleanly against a committed snapshot to catch doc drift.

---

## Test 6 — test_coverage_reviewer (test suite)

**Skills executed**: coverage.xml forensics, pytest suite inventory, mutation-testing readiness assessment.

### Findings

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| TC-01 | **P0** | **Overall line coverage is 29.8%**; `src.openscience.api` (entire REST layer) at **0.0%**, `api.models` 0.0%, `workers` 0.0% | `coverage.xml` line-rate="0.2981" |
| TC-02 | P1 | `tests/api/` directory is **empty** — zero route, auth, or schema tests despite a full JWT + session lifecycle surface | `ls tests/api` → empty |
| TC-03 | P1 | Only 10 test files exist for 154 source files; suite concentrates on `core/` (54.7% cov) | `find tests -name "*.py"` |
| TC-04 | P1 | `tests/integration/` exists but contains only prior experiment reports — no live integration tests | this report's home dir |
| TC-05 | P2 | No mutation testing wired (mutmut listed as agent skill but absent from dev deps and CI) | `pyproject.toml` |
| TC-06 | P2 | `docker-compose.test.yml` exists but CI `ci.yml` doesn't run the compose test stack, only in-repo pytest | `.github/workflows/ci.yml` |
| TC-07 | P3 | Positives: pytest config with asyncio + benchmark plugins present; coverage HTML published to `htmlcov/` | `pytest.ini`, `htmlcov/` |

### Recommendations

1. **Priority**: seed `tests/api/` with FastAPI `TestClient` suites: auth register/login/me, session CRUD, ownership enforcement (403 paths), analyze failure paths. Target: `api/` ≥ 70% within one iteration.
2. Add a coverage floor to CI (`--cov-fail-under=30` now, ratchet +5 per sprint).
3. Add one true integration test: spin compose test stack in CI and hit `/health` + one session round-trip.
4. Wire mutmut on `core/` only, weekly scheduled job, report-only.

**Fix attempt note**: no source fix taken here — coverage gaps require test authorship, not code edits; scaffolding belongs to a dedicated test-writing pass.

---

## Test 7 — database_reviewer (models & queries)

**Skills executed**: ORM model audit, query-pattern review (manual; sqlfluff N/A — no raw SQL), migration check, index analysis.

### Findings

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| DB-01 | P1 | **Single alembic migration** (`0001_initial_schema`) but `init_db()` also calls `Base.metadata.create_all` at API startup — two competing sources of schema truth; drift guaranteed | `database.py:51-57`, `main.py:92` |
| DB-02 | P1 | `UserModel.username`/`email` unique-indexed; registration flow does `SELECT` then `INSERT` without catching `IntegrityError` — race → 500 instead of 409 | `routes/auth.py:30-50` |
| DB-03 | P2 | JSON columns (`data_keys`, `loaded_data`, `parameters`, `result`) unbounded; no DB-level size cap; `result` payloads from analyses can be MBs — SQLite default is also the dev fallback while prod uses Postgres (dialect divergence on JSON operators) | `models/session.py`, `models/task.py` |
| DB-04 | P2 | Missing indexes for known query patterns: `tasks.created_at` used in `order_by` has no index; `sessions.owner_id+status` combo uncovered | `models/task.py`, `routes/sessions.py:331-335` |
| DB-05 | P2 | `session_registry` duplicates state the DB already owns (`data_keys` synced manually at `routes/sessions.py:174`) — denormalization without invalidation strategy | — |
| DB-06 | P3 | Globals `_engine`/`_SessionLocal` with hand-rolled reset — workable for tests but not thread-safe under engine churn | `database.py:13-66` |

### Recommendations

1. Remove `create_all` from startup path; gate on alembic `upgrade head`; keep `create_all` in tests only.
2. Wrap register `db.commit()` in `try/except IntegrityError` → 409.
3. Cap serialized payload sizes (pydantic `max_length` / app-level guard) before write; consider object-storage offload for large results.
4. Add indexes: `tasks(session_id, created_at)`, `sessions(owner_id, status)` in a new migration.
5. Standardize engine/session lifecycle via app state instead of module globals.

---

## Test 8 — api_design_reviewer (OpenAPI spec)

**Skills executed**: route-surface audit (FastAPI schema auto-generated), REST convention review, error-model consistency check. (Validator tools spectral/openapi-spec-validator not installed; audit performed against FastAPI's generated spec semantics.)

### Findings

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| AP-01 | P1 | **No authentication object documented per-operation in a discoverable way** + two API surfaces coexist (Flask `/api/agents` unauthenticated vs FastAPI `/api/v1/agents` JWT) — spec describes only half the real surface | see AR-01 |
| AP-02 | P1 | Session-scoped mutations return `TaskResponse` (201-ish semantics) but endpoints use POST without `Location` header / async-status affordance despite long-running work | `routes/sessions.py:193-315` |
| AP-03 | P2 | Inconsistent error shapes: FastAPI handlers emit `{detail, errors}` but Flask blueprint emits `{status, message}`; `ErrorResponse` model declared but not enforced on 400s from `_handle_execution_error` | `main.py:64-88`, `routes/sessions.py:127-141` |
| AP-04 | P2 | `GET /sessions/{id}/results` returns heterogeneous `results` dict keyed by description strings — unstable keys, poor client ergonomics | `routes/sessions.py:338-352` |
| AP-05 | P2 | No request-id propagation into `ErrorResponse` despite `RequestLoggingMiddleware` existing | `api/middleware/logging.py` |
| AP-06 | P3 | Version prefix `/api/v1` good; `/health` unversioned and duplicated in both stacks | `main.py:59-62`, `server.py:71-74` |
| AP-07 | P3 | Missing `ETag`/`If-Modified-Since` on `/results`; no cache directives anywhere | — |

### Recommendations

1. Unify error contract: one `ErrorResponse {detail, error, request_id}` everywhere; delete Flask shapes with the stack consolidation.
2. Return `202` + `Location: /api/v1/tasks/{id}` for analyze/visualize/write once worker offload lands (PF-01).
3. Make `/results` a list of `{key, task_id, created_at, summary}` objects rather than a dict.
4. Commit `openapi.json` snapshot to repo and diff it in CI (also feeds DOC-03).
5. Inject request id from middleware into all error payloads.

---

## Test 9 — accessibility_reviewer (UI)

**Skills executed**: manual WCAG 2.1 AA audit of both UIs (inline HTML template in `server.py` and React `ui/src/App.jsx`). axe-core/pa11y not runnable headlessly here without a live server.

### Findings

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| AC-01 | P1 | **XSS + a11y overlap**: `innerHTML` injection (SEC-02) can also inject arbitrary markup breaking landmark structure and screen-reader flow | `server.py:178-203` |
| AC-02 | P1 | Form inputs lack `<label>`s — `taskInput`/`specialistSelect` use placeholder text only (WCAG 3.3.2 / 4.1.2); React UI has no forms yet but agent list is a bare `<ul>` with no heading hierarchy past `h2` | `server.py:155-158`, `App.jsx:28-34` |
| AC-03 | P2 | Color contrast: gradient header `#667eea→#764ba2` over white text passes, but `.agent-category` `#666` on `#f8f9fa` ≈ 5.7:1 OK — however `button` focus style absent (2.4.7 focus visible) | `server.py` CSS |
| AC-04 | P2 | No `lang` attribute on `<html>`; no `<main>`/landmark roles; loading state "Loading..." not `aria-live` | `server.py:80`, `App.jsx:26` |
| AC-05 | P2 | Buttons have no `:focus-visible` outline; keyboard trap-free but focus order undocumented | CSS |
| AC-06 | P3 | Emoji-only iconography (🔬📊🤖) without `aria-label`/text alternatives | both UIs |
| AC-07 | P3 | `index.html` in `ui/` unverified for meta viewport/title lang; Vite default likely acceptable | `ui/index.html` |
| AC-08 | P3 | No axe-core/pa11y in CI; no a11y test at all | `ui/package.json` |

### Recommendations

1. Fix SEC-02 first (shared root cause), then add explicit `<label for>` and `aria-describedby` for helper text.
2. Add `lang="en"`, wrap content in `<main>`, make status region `aria-live="polite"`.
3. Add `:focus-visible` styles; add axe-core to the Vite test pipeline (`@axe-core/react` in dev).
4. Put `aria-hidden="true"` on decorative emoji or wrap with `role="img" aria-label`.

---

## Test 10 — devops_reviewer (Docker & CI/CD)

**Skills executed**: Dockerfile/compose audit (hadolint-style manual rules), CI workflow review, secrets handling scan, image hygiene assessment.

### Findings

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| DV-01 | **P0** | **Dev compose runs the API with `FLASK_DEBUG=1` and `--reload` exposed on `0.0.0.0:8080`** with the source tree mounted — remote debugger exposure if port is reachable; combined with stale SEC-01 fix this must never ship to prod profile | `docker-compose.yml:10-11,18-19,38` |
| DV-02 | P1 | Hardcoded DB password `openscience` in compose env committed to repo; `${SECRET_KEY:-dev-secret-key...}` default means production boot works with a known key if env unset | `docker-compose.yml:12,16,97-98` |
| DV-03 | P2 | `Dockerfile.api/ui/worker/test` divergence from root `Dockerfile` un-audited in-tree (not shown here); root `Dockerfile` is clean: multi-stage, non-root, slim, venv layer | `Dockerfile` |
| DV-04 | P2 | Postgres and Redis **ports published to host** (5432/6379) in dev compose — unnecessary lateral surface; Flower exposed without auth on 5555 | `docker-compose.yml:101-102,120-121,145` |
| DV-05 | P2 | CI matrix covers lint/type/test/security (CodeQL, SARIF upload — good) but no image scan (trivy/grype) despite agent skill claim; `docker.yml` builds but doesn't scan | `.github/workflows/docker.yml` |
| DV-06 | P3 | Healthchecks inconsistent: API curls `/health` (exists in both stacks), worker relies on celery ping (fine), Redis capped at 256mb LRU (fine) | compose |
| DV-07 | P3 | Dependabot configured; CODEOWNERS + PR template present; docs workflow separate | `.github/` |
| DV-08 | P3 | `docker-compose.override.yml.example` + `prod.yml` split is good practice; prod file un-audited here | root listing |

### Recommendations

1. **DV-01**: strip `FLASK_DEBUG` from the committed compose; move it to `docker-compose.override.yml.example` only.
2. **DV-02**: switch to `${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}` style required-vars; document `.env` workflow (`.env.example` exists — enforce its use in compose via `env_file`).
3. Stop publishing 5432/6379/5555 by default; use `expose:` internally; add basic auth or bind to localhost for Flower.
4. Add trivy image scan to `docker.yml` with SARIF upload alongside CodeQL.
5. Pin base images by digest (`python:3.12-slim@sha256:...`) for reproducible builds.

**Fix attempt note**: DV-01/DV-02 are compose-policy decisions (do teammates rely on the baked-in dev defaults?) — flagged rather than edited to avoid breaking colleagues' workflows. SEC-01 fix already removes the code-side debug default, so DV-01 is now the last remaining debug exposure.

---

## Cross-cutting Themes (from all 10 reviews)

1. **Dual-stack schizophrenia** (AR-01, AP-01, SEC-02): consolidate on FastAPI; delete or quarantine Flask surface. Highest-leverage single change.
2. **Docs outrunning code** (DOC-01/02, AR-02): the 111-agent catalog and architecture diagram describe aspirational state. Add "Status: planned/implemented" markers.
3. **Test vacuum at the edges** (TC-01/02): core is decent (54.7%), API/workers/models are 0%. Seed `tests/api/` first.
4. **Secrets & debug defaults** (SEC-01✅, SEC-03, DV-01/02): one fixed, three remain — all are env-guard one-liners.
5. **Sync-in-request execution** (PF-01, CQ-03): agent runs belong on the Celery fleet with 202 semantics; also resolves the async-boundary hack.

## P0 Disposition

| P0 Issue | Status |
|----------|--------|
| SEC-01 Flask `debug=True` hardcoded | ✅ **FIXED** — now env opt-in (`FLASK_DEBUG`); bandit B201 re-scan clean |
| TC-01 29.8% total coverage, API at 0% | 📋 Documented; requires test-writing sprint (recommendations TC §1-2) |
| DV-01 Debug + reload in committed compose | 📋 Documented with fix recipe; deferred to avoid breaking dev workflows |

## Tooling Appendix (what actually ran)

- `bandit 1.9.x -r src/` → 6 findings (1 High, 1 Medium, 4 Low) — High fixed this run
- `ruff check src/` → 22 findings (incl. 1 F821 undefined name, 2 F841 unused vars)
- `coverage.xml` parse → per-package coverage table (TC section)
- Manual audits: OWASP Top 10 (A01-A10), WCAG 2.1 AA spot checks, REST maturity model, 12-Factor compliance
- Not runnable in this environment: live axe-core, load testing, sqlfluff (no raw SQL), trivy (no built images)

*End of Experiment 09.*
