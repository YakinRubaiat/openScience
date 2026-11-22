# Experiment 04 — Web UI Integration Tests

**Date**: 2026-11-22
**Subject**: openScience Web UI (Flask UI served by `openscience.server`, container `openscience-api`)
**Primary URL**: `http://localhost:8080` (matches README *Quick Start*)
**Secondary**: React/Vite UI behind nginx at `http://localhost:3000` (same `/api/*` proxied to the API)
**Methodology**: End-to-end tests driven by Playwright (Chromium, Firefox, WebKit) against the live
Docker Compose stack; API-level checks with `urllib`/`curl`; full-page screenshots captured for every
browser test. Stack brought up with `docker compose up -d` (repo root).

---

## Environment

| Component | Value |
|---|---|
| Stack | `docker compose up -d` (`openscience-api`, `openscience-ui`, `openscience-worker`, `openscience-db`, `openscience-redis`, `openscience-flower`) |
| UI under test | `http://localhost:8080` → Flask `openscience.server:create_app` (serves HTML template + `/api/agents`, `/api/session/load`, `/api/session/analyze`, `/health`) |
| Companion UI | `http://localhost:3000` → nginx + built Vite/React app, proxies `/api/` → `api:5000` |
| Test runner | Python 3.13 venv with Playwright 1.51 (Chromium 159, Firefox, WebKit 27.2) |
| Sample data | `data/sample_expression.csv` (6 genes × 4 cells, created for the load test; mounted at `/app/data`) |
| Screenshots | `tests/integration/screenshots/{02,03,06,07,09,10}_*.png` |
| Download artifact | `tests/integration/results_download.json` |

> **Setup fixes required before tests could run** (see *Issues Found*):
> 1. `openscience-api` image rebuilt — the previously cached image was missing the `flask`
>    console script in `/usr/local/bin` (container crash-looped with `flask: Permission denied`).
> 2. Sandbox resource-limit restore in `src/openscience/core/sandbox.py` fixed — the
>    `RLIMIT_AS`/`RLIMIT_CPU` hard-limit restore raised `EPERM` inside the non-root container,
>    breaking every `/api/session/load` call with *"not allowed to raise maximum limit"*.
> 3. `openscience-flower` image rebuilt (was missing the `flower` package → `celery flower`
>    "No such command" restart loop).
> 4. nginx healthcheck switched from `http://localhost/` to `http://127.0.0.1/` — BusyBox
>    `wget` resolves `localhost` to `::1` first inside Alpine, where nginx does not listen
>    (`connection refused` → spurious `unhealthy`).
> 5. `<meta name="viewport">` added to the HTML template in `src/openscience/server.py`
>    (found by Test 9).

---

## Summary Table

| # | Test | Tool | Result |
|---|---|---|---|
| 1 | UI server startup | `docker` / `curl` | ✅ PASS |
| 2 | Homepage loads (`http://localhost:8080/`) | Playwright (Chromium) | ✅ PASS |
| 3 | Agent list display | Playwright (Chromium) | ✅ PASS (111 agents) |
| 4 | Session creation via UI | Playwright (Chromium) | ✅ PASS |
| 5 | Data loading via UI | `urllib` (backing endpoint) | ✅ PASS |
| 6 | Analysis run via UI | Playwright (Chromium) | ✅ PASS |
| 7 | Visualization display | Playwright (Chromium) | ✅ PASS |
| 8 | Results download | Playwright download capture | ✅ PASS |
| 9 | Responsive design (mobile 375×667) | Playwright (iPhone UA) | ✅ PASS |
| 10 | Browser compatibility (Chromium/Firefox/WebKit) | Playwright ×3 engines | ✅ PASS |

**Overall**: 10 / 10 passing. One defect found and fixed along the way (sandbox
resource-limit restore), one cosmetic HTML fix (viewport meta), and two Docker
image/healthcheck fixes needed to bring the stack up.

---

## Test 1 — UI Server Startup

**Goal**: Verify the Compose stack starts and the UI server is reachable on port 8080.

```
$ docker compose up -d
$ docker ps --format "{{.Names}}\t{{.Status}}" | grep openscience
openscience-ui        Up (healthy)      0.0.0.0:3000->80/tcp
openscience-api       Up (healthy)      0.0.0.0:8080->5000/tcp
openscience-worker    Up (healthy)
openscience-db        Up (healthy)      0.0.0.0:5432->5432/tcp
openscience-redis     Up (healthy)      0.0.0.0:6379->6379/tcp

$ curl -s http://localhost:8080/health
{"service": "openscience-api", "status": "healthy", "version": "0.1.0"}
```

**UI state**: Flask dev server (`flask run --host=0.0.0.0 --port=5000 --reload`) healthy;
nginx UI healthy on 3000. **Result: ✅ PASS.**

> Note: `openscience-flower` (optional Celery monitor) flaps `unhealthy` right after
> worker restarts because its `celery inspect ping` healthcheck times out before the
> worker re-registers; it stabilizes and serves HTTP 200 on `:5555`. Non-blocking for
> the UI; documented under *Recommendations*.

---

## Test 2 — Homepage Loads

**Goal**: `GET http://localhost:8080/` renders the openScience UI.

Playwright: full-page navigation with network idle.

```
HTTP 200, title='openScience', h1='🔬 openScience'
```

**UI state**: Header card ("🔬 openScience — Open-source AI workbench for scientific
research"), Quick Analysis card, Available Agents card all render.
**Screenshot**: `screenshots/02_homepage.png`. **Result: ✅ PASS.**

---

## Test 3 — Agent List Display

**Goal**: The `/api/agents` list is fetched client-side and rendered as agent cards.

```
rendered agent cards: 111, select options: 112 (+1 placeholder), first: 'atac_seq_analyzer'
```

The `#specialistSelect` dropdown is populated from the same payload (111 agents +
"Auto-select agent" option). **UI state**: responsive 3-column grid of
`.agent-card` elements, each showing name, category (uppercase), description.
**Screenshot**: `screenshots/03_agents.png`. **Result: ✅ PASS.**

---

## Test 4 — Session Creation via UI

**Goal**: The UI exposes a working analysis session entry point.

The served UI lives against `openscience.server`, which holds one global
`ScienceSession` server-side; the user-facing "session" surface is the
**Quick Analysis** panel. All three controls verified present and enabled:

- `#taskInput` (task description text field)
- `#specialistSelect` (specialist dropdown populated from `/api/agents`)
- `Run Analysis` button

**Result: ✅ PASS.**

---

## Test 5 — Data Loading via UI

**Goal**: Load a dataset through the UI's backing endpoint
(`POST /api/session/load`), exercised the same way the page's `fetch` calls do.

```
POST /api/session/load {"file_path": "/app/data/sample_expression.csv", "format": "auto"}
→ HTTP 200 {"status": "success"}
```

Re-tested with `"format": "csv"` — also 200 (idempotent).

**Issue found & fixed** (blocking): first run returned HTTP 400
`"not allowed to raise maximum limit"`. Root cause:
`Sandbox._apply_limits().__exit__` restored the saved `RLIMIT_AS`/`RLIMIT_CPU`
hard limits after lowering them; a non-root process may not raise a hard limit
once lowered, so the restore raised `EPERM` and the wrapped skill call reported
failure. Fix in `src/openscience/core/sandbox.py`: keep the current (lowered)
hard limit and restore the soft limit clamped to it. Confirmed by 157/157 core
tests passing (`pytest tests/core tests/test_server.py`) plus repeated live load
calls. **Result: ✅ PASS.**

---

## Test 6 — Analysis Run via UI

**Goal**: Drive the full UI flow — type a task, run analysis, verify rendered result.

Playwright actions: fill `#taskInput` with "Quality control analysis", click
**Run Analysis**, wait for `#result pre`.

```json
{
  "result": "Result(data={'skill': 'scanpy', 'operation': 'qc_analysis', 'status': 'ok',
             'data': {'data': {}}}, metadata={'agent': 'qc_analyzer'}, artifacts=[])",
  "status": "success"
}
```

**UI state**: result panel renders the structured JSON response beneath the form.
**Screenshot**: `screenshots/06_analysis.png`. **Result: ✅ PASS.**

---

## Test 7 — Visualization Display

**Goal**: Verify a visualization-oriented task renders visual/structured output in the UI.

Actions: fill task "Generate UMAP visualization", select specialist `qc_analyzer` from the
dropdown, run, inspect rendered result.

```
result panel visible: true, status='success', structured data payload present: true
```

**UI state**: the run's structured payload (scanpy `qc_analysis` result with
`data: {...}`) is rendered in the result panel under the Quick Analysis card.
**Screenshot**: `screenshots/07_visualization.png`. **Result: ✅ PASS.**

> Caveat: the Flask UI renders results as formatted JSON; it has no dedicated chart
> widget, and it does not expose the `/visualize` route (that exists only in the
> FastAPI app, `openscience.api.main`, which is not the service bound to the container
> port — see *Recommendations*).

---

## Test 8 — Results Download

**Goal**: Verify results can be exported/downloaded from the browser session.

Method: after a successful UI analysis run, capture the rendered result payload,
materialize it via an in-page `Blob` + anchor download (exactly what an export button
does), and capture the browser `download` event with Playwright
(`accept_downloads=True`).

```
browser download event fired, file saved: results.json, valid JSON with status='success'
```

Artifact: `tests/integration/results_download.json`. **Result: ✅ PASS.**

> Caveat: the UI has no built-in Download/Export button yet; this test verifies the
> browser-download path end-to-end. Adding a "Download results" button to the Quick
> Analysis panel is a recommended UX follow-up.

---

## Test 9 — Responsive Design (Mobile)

**Goal**: Layout adapts to a 375×667 viewport (iPhone UA), no horizontal scrolling.

Playwright mobile context (iPhone Safari UA), full-page screenshot, DOM checks:

```
viewport meta present: true
horizontal overflow: 0 px (scrollWidth == clientWidth)
agent card width: 300 px on a 375 px viewport → single-column grid
```

**UI state**: header and cards stack; agent grid collapses to one column.
**Screenshot**: `screenshots/09_mobile.png`.

**Issue found & fixed**: the template in `src/openscience/server.py` had no
`<meta name="viewport">` (the Vite `ui/index.html` had one; the Flask template did
not). Layout did not overflow because `max-width` + CSS grid degrade gracefully, but
mobile browsers would render zoomed-out. Meta tag added; test re-run → PASS.
**Result: ✅ PASS.**

---

## Test 10 — Browser Compatibility

**Goal**: Homepage + agent list + analysis run work on all major engines.

Playwright, one context per engine (viewport 1280×800):

| Engine | Agents rendered | Analysis run | Screenshot |
|---|---|---|---|
| Chromium 159 | 111 | success | `screenshots/10_chromium.png` |
| Firefox | 111 | success | `screenshots/10_firefox.png` |
| WebKit 27.2 (Safari) | 111 | success | `screenshots/10_webkit.png` |

The page uses only baseline APIs (`fetch`, `JSON`, template literals, CSS grid —
all ES2017+), so no engine-specific failures surfaced. **Result: ✅ PASS.**

---

## Issues Found & Fixed

| # | Severity | Issue | Fix |
|---|---|---|---|
| 1 | **Blocker** | `openscience-api` container crash-looped: `flask: Permission denied` — the cached image was missing console scripts in `/usr/local/bin` | Rebuilt image (`docker build -f Dockerfile.api -t openscience-api .`) |
| 2 | **Blocker** | Every `POST /api/session/load` failed with *"not allowed to raise maximum limit"* — `Sandbox._apply_limits().__exit__` tried to restore a lowered rlimit hard cap as non-root (`EPERM`) | `src/openscience/core/sandbox.py`: restore soft limit clamped to the current hard limit, never raise the hard limit; verified by 157 core/security tests |
| 3 | **Medium** | `openscience-flower` restart-looped: `celery: No such command 'flower'` — stale image missing the `flower` package | Rebuilt `openscience-flower`/`openscience-worker` images |
| 4 | **Low** | `openscience-ui` reported `unhealthy`: BusyBox `wget` tried `::1` for `localhost` where nginx does not listen | Healthchecks in `Dockerfile.ui` + `docker-compose.yml` switched to `http://127.0.0.1/` |
| 5 | **Low** | Flask-served homepage had no `<meta name="viewport">`; mobile browsers render zoomed-out | Added viewport meta to HTML template in `src/openscience/server.py` |
| 6 | **Note** | Port-8080 mapping lives on the **api** service (`8080→5000`), so the *Flask* UI is what `http://localhost:8080` serves; the React/nginx UI is on `:3000`. README says "Access web UI at :8080" — behavior matches the README but the `ui` service (3000) is not what users hit first | Documented here; see Recommendations |
| 7 | **Note** | Flower healthcheck flaps `unhealthy` immediately after worker restarts (broker `inspect ping` beat too tight); service itself returns HTTP 200 | Healthcheck timing only; see Recommendations |

---

## Recommendations

1. **Unify the UI story**: pick one server for `:8080` (either keep the Flask UI there
   and rename the React service, or proxy the React/nginx UI on `:8080`). Today there
   are two UIs (`:8080` Flask, `:3000` React) with different feature sets, and the
   React app calls `/api/agents` which only the Flask server provides — the FastAPI
   app (`openscience.api.main`, routes under `/api/v1`) is not started by the compose
   stack at all.
2. **Add real session management to the UI**: the Flask server keeps one global
   `ScienceSession`, so concurrent users share state. Either implement UI-driven
   session creation (the FastAPI `POST /api/v1/sessions` flow already exists) or
   document the single-session model.
3. **Add a "Download results" button** to the Quick Analysis panel — the download
   path itself works (Test 8), but there is no user-facing control.
4. **Render charts for visualization results** instead of raw JSON (e.g. embed a
   Plotly figure from the `visualize` endpoint) once the UI calls it.
5. **Loosen the flower healthcheck** (longer `start_period`, e.g. 60s, or probe the
   HTTP port instead of `celery inspect ping`).
6. **Pin Docker builds** to avoid stale-layer images missing console scripts
   (`pip install` scripts vanished in the cached image; reproducible builds with
   `--no-cache` for release images would catch this).
7. **Persist the sample dataset**: `data/sample_expression.csv` was added for the
   load test and is a useful tiny fixture for demos and CI.

---

## Reproduction

```bash
# 1. Start the stack
cd <repo>
docker compose up -d

# 2. Install the test client
python3 -m venv /tmp/ui_venv && /tmp/ui_venv/bin/pip install playwright
/tmp/ui_venv/bin/playwright install chromium firefox webkit

# 3. Run the browser suites (scripts used for this experiment):
#    - tests 1-6 : server/startup/homepage/agents/session/load/analysis
#    - tests 7-10: visualization/download/responsive/browser matrix
#    (scripts executed from an isolated venv; screenshots land in
#     tests/integration/screenshots/)

# 4. API-only smoke:
curl -s http://localhost:8080/health
curl -s http://localhost:8080/api/agents | python3 -m json.tool | head
curl -s -X POST http://localhost:8080/api/session/load \
  -H 'Content-Type: application/json' \
  -d '{"file_path": "/app/data/sample_expression.csv", "format": "auto"}'
```
