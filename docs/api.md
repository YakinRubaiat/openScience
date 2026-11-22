# API Reference

The openScience REST API is served by the `api` service on port **8000**.
All endpoints are prefixed with `/api/v1`.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Local development runs without authentication. In production deployments,
pass a bearer token:

```bash
curl -H "Authorization: Bearer $OPENSCIENCE_TOKEN" \
  http://localhost:8000/api/v1/sessions
```

## Health

### GET /health

Liveness probe. Returns 200 when the API is up.

```bash
curl http://localhost:8000/api/v1/health
```

```json
{"status": "ok"}
```

## Sessions

### POST /sessions

Create a new analysis session.

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Quality control and clustering",
    "specialist": "scanpy_specialist",
    "data": "data/pbmc_10k.h5ad"
  }'
```

```json
{
  "id": "sess_01H9K2...",
  "status": "created",
  "task": "Quality control and clustering"
}
```

### GET /sessions

List sessions.

```bash
curl http://localhost:8000/api/v1/sessions
```

### GET /sessions/{id}

Fetch a single session, including its status and artifact references.

```bash
curl http://localhost:8000/api/v1/sessions/sess_01H9K2...
```

```json
{
  "id": "sess_01H9K2...",
  "status": "complete",
  "task": "Quality control and clustering",
  "artifacts": ["art_umap_pdf", "art_methods_md"]
}
```

## Tasks

### POST /sessions/{id}/tasks

Submit a follow-up task to an existing session.

```bash
curl -X POST http://localhost:8000/api/v1/sessions/sess_01H9K2.../tasks \
  -H "Content-Type: application/json" \
  -d '{"task": "Differential expression, cluster 3 vs cluster 1"}'
```

### GET /tasks/{id}

Poll a task's status. Statuses are `queued`, `running`, `awaiting_approval`,
`complete`, and `failed`.

```bash
curl http://localhost:8000/api/v1/tasks/task_42X7...
```

## Agents

### GET /agents

List all 100 specialist agents with their categories and skill sets.

```bash
curl http://localhost:8000/api/v1/agents
curl "http://localhost:8000/api/v1/agents?category=Data%20Analysis"
```

### GET /agents/{name}

Details for one agent — description, skills, declared inputs and outputs.

```bash
curl http://localhost:8000/api/v1/agents/scanpy_specialist
```

## Artifacts

### GET /artifacts/{id}

Download an artifact. Every artifact includes provenance metadata: the code,
data versions, and parameters that produced it.

```bash
curl -O http://localhost:8000/api/v1/artifacts/art_umap_pdf
```

### GET /artifacts/{id}/provenance

Fetch the full provenance graph for an artifact.

```bash
curl http://localhost:8000/api/v1/artifacts/art_umap_pdf/provenance
```

## Approvals

The human-approval broker queues privileged actions (code execution, network
egress, deletions). Until approved, the requesting task stays in
`awaiting_approval`.

### GET /approvals

List pending approval requests.

```bash
curl http://localhost:8000/api/v1/approvals
```

### POST /approvals/{id}/approve

Approve a pending action.

```bash
curl -X POST http://localhost:8000/api/v1/approvals/appr_8Qz.../approve
```

### POST /approvals/{id}/deny

Deny a pending action.

```bash
curl -X POST http://localhost:8000/api/v1/approvals/appr_8Qz.../deny
```

## Error Format

Errors follow a consistent shape:

```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "No session with id sess_01H9K2..."
  }
}
```

| HTTP status | Meaning |
|-------------|---------|
| 400 | Malformed request body or parameters |
| 401 | Missing or invalid token (production) |
| 404 | Resource not found |
| 409 | Conflict (e.g., task already running) |
| 500 | Internal error |

## Related

- [Getting Started](getting-started.md) — start the API
- [Configuration](configuration.md) — ports, auth, and CORS settings
- [Architecture](architecture.md) — where the API sits in the system
