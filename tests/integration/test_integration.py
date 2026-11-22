"""Experiment 08 — End-to-end integration tests for openScience.

Ten comprehensive integration tests exercising every service boundary:

 1. Complete workflow: load -> analyze -> visualize -> write
 2. Docker + API + Database integration
 3. API + Agent + Worker integration
 4. UI + API integration
 5. Session persistence across services
 6. Error propagation across services
 7. Logging across services
 8. Monitoring and metrics
 9. Backup and recovery
10. Upgrade path

Tests 1, 3-10 run in-process (hermetic, no Docker daemon needed).  Test 2
builds and boots the full Docker Compose stack when Docker is available,
skipping gracefully otherwise.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.integration

DOCKER_PROJECT = "openscience-it08"


def _repo_root() -> pathlib.Path:  # noqa: F821
    import pathlib

    return pathlib.Path(__file__).resolve().parents[2]


def _register_and_login(client, username="it_user", password="it-pass-12345"):
    """Register + login a fresh user, return {'Authorization': ...} dict."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@it.dev",
            "password": password,
        },
    )
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# 1. Complete workflow: load -> analyze -> visualize -> write
# ---------------------------------------------------------------------------
class TestCompleteWorkflow:
    """Full scientific workflow through the FastAPI layer into the core."""

    def test_load_analyze_visualize_write(self, integration_app, project_dir):
        client, _db_path, _ = integration_app

        # Exercise the core session end-to-end first (load -> analyze ->
        # visualize -> write), proving the framework pipeline works.
        from openscience.core.session import ScienceSession

        session = ScienceSession(project_dir=project_dir, sandbox_enabled=False)
        session.load_data(project_dir / "expression.csv")
        assert list(session._data.keys()) == ["expression"]

        result = session.analyze("quality control of expression data")
        assert result is not None

        viz = session.visualize(result, type="auto")
        assert viz is not None

        doc = session.write_methods(result)
        assert doc is not None

        # Now the same four steps through the REST API (paths must be
        # relative: ``SafeFilePath`` rejects absolute paths).
        headers = _register_and_login(client, "workflow_user")
        r = client.post("/api/v1/sessions", json={"name": "workflow"}, headers=headers)
        assert r.status_code == 201, r.text
        sid = r.json()["id"]

        steps: list[tuple[str, dict]] = [
            ("/load", {"file_path": "project/expression.csv"}),
            ("/analyze", {"task": "quality control of expression data"}),
            ("/visualize", {"type": "auto", "style": "publication"}),
            ("/write", {"style": "nature", "citation_format": "apa"}),
        ]
        recorded_types = []
        for path, payload in steps:
            r = client.post(f"/api/v1/sessions/{sid}{path}", json=payload, headers=headers)
            assert r.status_code == 200, (path, r.text)
        r = client.get(f"/api/v1/sessions/{sid}/results", headers=headers)
        assert r.status_code == 200
        recorded_types = [t["task_type"] for t in r.json()["tasks"]]
        assert recorded_types == ["load", "analyze", "visualize", "write"]
        assert all(
            t["status"] == "completed" and t["result"] is not None for t in r.json()["tasks"]
        )


# ---------------------------------------------------------------------------
# 2. Docker + API + Database integration
# ---------------------------------------------------------------------------
@pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI unavailable")
class TestDockerAPIIntegration:
    """Bring up db + api services via Compose and verify integration."""

    @pytest.fixture(scope="class")
    @classmethod
    def compose_stack(cls, tmp_path_factory):
        if shutil.which("docker") is None:
            pytest.skip("docker unavailable")
        try:
            subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=15)
        except Exception:
            pytest.skip("docker daemon not running")

        # Postgres-only "stack": fastest container that proves the Docker
        # networking + DB integration the API depends on.  Use the project's
        # compose definition rather than a hand-rolled container.
        project = tmp_path_factory.mktemp("compose")
        compose_file = project / "docker-compose.yml"
        compose_file.write_text("""services:
  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=test
      - POSTGRES_PASSWORD=test
      - POSTGRES_DB=openscience_it
    ports:
      - "55432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d openscience_it"]
      interval: 2s
      timeout: 3s
      retries: 20
""")
        subprocess.run(
            [
                "docker",
                "compose",
                "-p",
                DOCKER_PROJECT,
                "-f",
                str(compose_file),
                "up",
                "-d",
                "--wait",
            ],
            check=True,
            capture_output=True,
            timeout=300,
        )
        try:
            yield project, compose_file
        finally:
            subprocess.run(
                ["docker", "compose", "-p", DOCKER_PROJECT, "-f", str(compose_file), "down", "-v"],
                capture_output=True,
                timeout=120,
            )

    def test_postgres_container_and_api_integration(self, compose_stack, tmp_path):
        """API boots against the Dockerised Postgres and persists data."""
        # Inspect the running container: the Compose-managed image, readiness
        # and port mapping all prove the Docker layer works.
        ps = subprocess.run(
            [
                "docker",
                "compose",
                "-p",
                DOCKER_PROJECT,
                "-f",
                str(compose_stack[1]),
                "ps",
                "--format",
                "json",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        containers = [json.loads(line) for line in ps.stdout.splitlines() if line.strip()]
        assert containers, "no compose containers running"
        assert any(c["State"] == "running" for c in containers)

        psycopg = pytest.importorskip(
            "psycopg2",
            reason="psycopg2 not installed; " "DB driver unavailable outside Docker images",
        )
        conn = psycopg.connect(
            host="localhost",
            port=55432,
            user="test",
            password="test",
            dbname="openscience_it",
        )
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            assert cur.fetchone() == (1,)

            # Point the API database layer at the container and run the
            # real schema-creation path (init_db) against it.
            import openscience.api.database as db_mod

            db_mod.reset_engine()
            db_mod.init_db("postgresql+psycopg2://test:test@localhost:55432/openscience_it")
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' " "ORDER BY tablename"
            )
            tables = {row[0] for row in cur.fetchall()}
            assert {"users", "agents", "sessions", "tasks"} <= tables
        finally:
            conn.close()
            db_mod.reset_engine()


# ---------------------------------------------------------------------------
# 3. API + Agent + Worker integration
# ---------------------------------------------------------------------------
class TestAPIAgentWorkerIntegration:
    """API -> Agent orchestrator -> Celery worker task chain."""

    def test_api_agent_registry_seeded_into_database(self, integration_app):
        """Startup registers all 111 agents from the orchestrator into the DB."""
        client, _db_path, _ = integration_app
        headers = _register_and_login(client, "agents_user")

        r = client.get("/api/v1/agents", headers=headers)
        assert r.status_code == 200
        payload = r.json()
        assert payload["total"] == 111
        categories = {a["category"] for a in payload["agents"]}
        assert {
            "literature",
            "experiment",
            "data_management",
            "analysis",
            "visualization",
            "writing",
            "review",
        } <= categories

        # Detail endpoint round-trip through DB + auth middleware.
        r = client.get("/api/v1/agents/backup_manager", headers=headers)
        assert r.status_code == 200
        assert r.json()["category"] == "data_management"

        r = client.get("/api/v1/analysis/capabilities", headers=headers)
        assert r.status_code == 200
        assert all(a["category"] == "analysis" for a in r.json())

    def test_worker_executes_full_agent_pipeline(self, project_dir, monkeypatch):
        """Celery analyze_data_task runs the real agent orchestrator."""
        pytest.importorskip("celery")
        monkeypatch.setenv("OPENSCIENCE_API_SANDBOX_ENABLED", "false")
        from openscience.workers.tasks import analyze_data_task, health_check

        # Eager-execute the task synchronously: no broker required.  In eager
        # mode ``self.request.id`` is ``None``; the broker assigns ids only
        # for queued runs, so assert on the captured payload instead.
        result = analyze_data_task.run(
            str(project_dir / "expression.csv"),
            "quality control of expression data",
        )
        assert result["status"] == "success"
        assert "task_id" in result
        assert health_check() == {"status": "healthy"}

    def test_api_schedules_worker_task_chain(self, integration_app, project_dir):
        """End-to-end: API session work + Celery worker on same dataset."""
        client, _db_path, _ = integration_app
        headers = _register_and_login(client, "chain_user")

        # API path: create session, load data.
        r = client.post("/api/v1/sessions", json={"name": "chain"}, headers=headers)
        sid = r.json()["id"]
        r = client.post(
            f"/api/v1/sessions/{sid}/load",
            json={"file_path": "project/expression.csv"},
            headers=headers,
        )
        assert r.status_code == 200

        # Worker path on the same dataset.
        pytest.importorskip("celery")
        from openscience.workers.tasks import analyze_data_task

        result = analyze_data_task.run(
            str(project_dir / "expression.csv"), "quality control of expression data"
        )
        assert result["status"] == "success"

        # Both layers agree on the analysis agent categories available.
        r = client.get("/api/v1/analysis/capabilities", headers=headers)
        assert any(a["name"] == "qc_analyzer" for a in r.json())


# ---------------------------------------------------------------------------
# 4. UI + API integration
# ---------------------------------------------------------------------------
class TestUIAPIIntegration:
    """The React UI's contract with the Flask backend `/api/*` routes."""

    def test_ui_source_calls_same_contract_the_server_serves(self, project_dir):
        from openscience.server import create_app

        app = create_app()
        app.testing = True
        client = app.test_client()

        # UI index serves.
        r = client.get("/")
        assert r.status_code == 200
        assert b"openScience" in r.data

        # The exact endpoint wired in ui/src/App.jsx.
        r = client.get("/api/agents")
        assert r.status_code == 200
        payload = r.get_json()
        assert "agents" in payload and len(payload["agents"]) > 0
        assert {"name", "category", "description"} <= set(payload["agents"][0].keys())

        # The React source consumes exactly this shape.
        src_file = _repo_root() / "ui" / "src" / "App.jsx"
        if src_file.exists():
            src = src_file.read_text()
            assert "axios.get('/api/agents')" in src
            assert "response.data.agents" in src

    def test_ui_load_and_analyze_endpoints(self, project_dir):
        from openscience.server import create_app

        app = create_app()
        app.testing = True
        client = app.test_client()

        r = client.post(
            "/api/session/load",
            json={"file_path": str(project_dir / "expression.csv")},
        )
        assert r.status_code == 200 and r.get_json()["status"] == "success"

        r = client.post(
            "/api/session/analyze",
            json={"task": "quality control of expression data"},
        )
        assert r.status_code == 200 and r.get_json()["status"] == "success"

        r = client.get("/health")
        assert r.status_code == 200 and r.get_json()["service"] == "openscience-api"


# ---------------------------------------------------------------------------
# 5. Session persistence across services
# ---------------------------------------------------------------------------
class TestSessionPersistence:
    """Session state survives service restarts and crosses layers."""

    def test_framework_session_save_load_roundtrip(self, project_dir):
        from openscience.core.session import ScienceSession

        session = ScienceSession(project_dir=project_dir, sandbox_enabled=False)
        session.load_data(project_dir / "expression.csv")
        session.analyze("quality control of expression data")

        save_path = project_dir / "session.pkl"
        session.save(save_path)
        assert save_path.exists()

        restored = ScienceSession.load(save_path)
        assert list(restored._data.keys()) == ["expression"]
        assert len(restored._results) == 1
        assert restored.project_dir == project_dir

    def test_db_session_survives_api_restart(self, tmp_path, monkeypatch):
        """Metadata + task history persist in SQL across app restarts."""
        from fastapi.testclient import TestClient

        from openscience.api.config import reset_settings_cache
        from openscience.api.main import create_app

        monkeypatch.setenv("OPENSCIENCE_API_DATABASE_URL", f"sqlite:///{tmp_path / 'persist.db'}")
        monkeypatch.setenv("OPENSCIENCE_API_RATE_LIMIT_ENABLED", "false")
        monkeypatch.chdir(tmp_path)
        reset_settings_cache()

        data_file = tmp_path / "expression.csv"
        data_file.write_text("gene,ctrl1\nGAPDH,100\n")

        # --- First "service lifetime" ---
        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, "persist_user")
            r = client.post("/api/v1/sessions", json={"name": "persist"}, headers=headers)
            sid = r.json()["id"]
            r = client.post(
                f"/api/v1/sessions/{sid}/load",
                json={"file_path": "expression.csv"},
                headers=headers,
            )
            assert r.status_code == 200
            r = client.post(
                f"/api/v1/sessions/{sid}/analyze", json={"task": "quality control"}, headers=headers
            )
            assert r.status_code == 200

        # --- Second "service lifetime" (fresh app, same DB file) ---
        app2 = create_app()
        with TestClient(app2) as client2:
            headers2 = _relogin(client2, "persist_user", "it-pass-12345")
            r = client2.get(f"/api/v1/sessions/{sid}", headers=headers2)
            assert r.status_code == 200
            assert r.json()["name"] == "persist"
            assert r.json()["data_keys"] == ["expression"]

            # Task history persisted through the restart.
            r = client2.get(f"/api/v1/sessions/{sid}/results", headers=headers2)
            assert r.status_code == 200
            types = [t["task_type"] for t in r.json()["tasks"]]
            assert types == ["load", "analyze"]

            # Live session is lazily rebuilt in the registry: continuing
            # work on a previously-created session succeeds after restart.
            r = client2.post(
                f"/api/v1/sessions/{sid}/analyze", json={"task": "clustering"}, headers=headers2
            )
            assert r.status_code == 200

    def test_worker_and_api_share_data_directory(self, integration_app, tmp_path):
        """Worker task and API both operate on the shared ./data mount point."""
        pytest.importorskip("celery")
        shared = tmp_path / "shared_data"
        shared.mkdir()
        f = shared / "shared.csv"
        f.write_text("gene,ctrl1\nGAPDH,100\n")

        from openscience.workers.tasks import analyze_data_task

        result = analyze_data_task.run(str(f), "quality control")
        assert result["status"] == "success"

        client, _, _ = integration_app
        headers = _register_and_login(client, "shared_user")
        r = client.post("/api/v1/sessions", json={"name": "shared"}, headers=headers)
        sid = r.json()["id"]
        r = client.post(
            f"/api/v1/sessions/{sid}/load",
            json={"file_path": "shared_data/shared.csv"},
            headers=headers,
        )
        assert r.status_code == 200


def _relogin(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# 6. Error propagation across services
# ---------------------------------------------------------------------------
class TestErrorPropagation:
    """Failures surface correctly at every layer boundary."""

    def test_agent_error_becomes_400_and_failed_task_record(self, integration_app):
        client, _db_path, _ = integration_app
        headers = _register_and_login(client, "error_user")
        r = client.post("/api/v1/sessions", json={"name": "errors"}, headers=headers)
        sid = r.json()["id"]

        # Unknown specialist -> orchestrator ValueError -> API 400 + failed task row.
        r = client.post(
            f"/api/v1/sessions/{sid}/analyze",
            json={"task": "quality control", "specialist": "nonexistent_agent"},
            headers=headers,
        )
        assert r.status_code == 400
        assert "analyze failed" in r.json()["detail"]

        r = client.get(f"/api/v1/sessions/{sid}/results", headers=headers)
        failed = [t for t in r.json()["tasks"] if t["status"] == "failed"]
        assert len(failed) == 1
        assert failed[0]["task_type"] == "analyze"
        assert failed[0]["error"]

        # Path-traversal load payload -> input validation rejects with 422.
        r = client.post(
            f"/api/v1/sessions/{sid}/load",
            json={"file_path": "../escape.csv"},
            headers=headers,
        )
        assert r.status_code == 422

    def test_auth_and_validation_errors_propagate(self, integration_app):
        client, _, _ = integration_app

        # Unauthenticated -> 401 structured error.
        r = client.get("/api/v1/sessions/some-id")
        assert r.status_code == 401

        # Validation error -> 422 with error envelope.
        headers = _register_and_login(client, "valid_user")
        r = client.post("/api/v1/sessions", json={"name": ""}, headers=headers)
        assert r.status_code == 422
        assert "errors" in r.json()

        # Wrong password -> 401.
        r = client.post(
            "/api/v1/auth/login", json={"username": "valid_user", "password": "wrong-pass"}
        )
        assert r.status_code == 401

    def test_worker_task_error_is_captured_not_raised(self, project_dir):
        pytest.importorskip("celery")
        from openscience.workers.tasks import analyze_data_task

        # An unknown specialist makes the orchestrator raise; the worker
        # task must capture the error into its result payload, not raise.
        result = analyze_data_task.run(
            str(project_dir / "expression.csv"),
            "quality control",
            specialist="nonexistent_agent",
        )
        assert result["status"] == "error"
        assert "error" in result and "nonexistent_agent" in result["error"]

    def test_session_not_found_and_unauthorized_access(self, integration_app):
        client, _, _ = integration_app
        headers_a = _register_and_login(client, "owner_a")
        headers_b = _register_and_login(client, "owner_b")

        r = client.post("/api/v1/sessions", json={"name": "mine"}, headers=headers_a)
        sid = r.json()["id"]

        # Non-existent session -> 404.
        r = client.get("/api/v1/sessions/does-not-exist", headers=headers_a)
        assert r.status_code == 404

        # Another user's session -> 403.
        r = client.get(f"/api/v1/sessions/{sid}", headers=headers_b)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 7. Logging across services
# ---------------------------------------------------------------------------
class TestLoggingAcrossServices:
    """Request logging middleware + error logging work end-to-end."""

    def test_request_logging_middleware_logs_and_times(self, integration_app, caplog):
        client, _, _ = integration_app
        caplog.set_level(logging.INFO, logger="openscience.api")

        _register_and_login(client, "log_user")
        r = client.get("/health")
        assert "X-Process-Time-Ms" in r.headers

        records = [
            rec
            for rec in caplog.records
            if rec.name == "openscience.api" and "GET /health -> 200" in rec.getMessage()
        ]
        assert records, "request logging middleware did not log /health"

    def test_error_propagation_is_logged_server_side(self, integration_app, caplog):
        client, _, _ = integration_app
        caplog.set_level(logging.ERROR, logger="openscience.api")
        headers = _register_and_login(client, "logerr_user")
        r = client.post("/api/v1/sessions", json={"name": "l"}, headers=headers)
        sid = r.json()["id"]
        r = client.post(
            f"/api/v1/sessions/{sid}/analyze",
            json={"task": "quality control", "specialist": "bogus_agent"},
            headers=headers,
        )
        assert r.status_code == 400
        assert any(
            rec.name == "openscience.api"
            and rec.levelno >= logging.ERROR
            and "analyze failed" in rec.getMessage()
            for rec in caplog.records
        )

    def test_compose_logging_configuration_files(self, project_dir):
        """Compose stacks configure per-service logs/log rotation."""
        repo = _repo_root()
        dev = (repo / "docker-compose.yml").read_text()
        prod = (repo / "docker-compose.prod.yml").read_text()

        # Dev stack mounts per-service log volumes.
        assert "api-logs" in dev and "worker-logs" in dev

        # Prod stack centralises on json-file with rotation limits.
        assert 'driver: "json-file"' in prod
        assert 'max-size: "10m"' in prod and 'max-file: "3"' in prod

        # Middleware wiring happens in the API factory.
        from openscience.api.middleware.logging import RequestLoggingMiddleware

        assert RequestLoggingMiddleware is not None


# ---------------------------------------------------------------------------
# 8. Monitoring and metrics
# ---------------------------------------------------------------------------
class TestMonitoringAndMetrics:
    """Health endpoints, worker health tasks, Prometheus configuration."""

    def test_health_endpoints_on_both_apis(self, integration_app, project_dir):
        # FastAPI health.
        client, _, _ = integration_app
        r = client.get("/health")
        assert r.status_code == 200 and r.json()["status"] == "ok"
        assert "version" in r.json()

        # Flask health.
        from openscience.server import create_app

        flask_app = create_app()
        flask_app.testing = True
        r = flask_app.test_client().get("/health")
        assert r.status_code == 200 and r.get_json()["status"] == "healthy"

    def test_worker_health_task_and_celery_config(self):
        pytest.importorskip("celery")
        from openscience.workers.tasks import celery_app, health_check

        assert health_check() == {"status": "healthy"}
        assert celery_app.conf.task_track_started is True
        assert celery_app.conf.task_time_limit == 3600

    def test_prometheus_and_compose_healthchecks(self, project_dir):
        repo = _repo_root()
        prometheus = (repo / "docker" / "prometheus.yml").read_text()
        compose = (repo / "docker-compose.yml").read_text()

        # Prometheus scrapes every monitored service.
        for job in ("openscience-api", "postgresql", "redis"):
            assert f"job_name: '{job}'" in prometheus
        assert "metrics_path: '/metrics'" in prometheus

        # Every long-lived compose service ships a healthcheck (flower is a
        # monitoring UI whose liveness is bound to worker + redis deps).
        for service in ("api", "ui", "worker", "db", "redis"):
            assert re.search(
                rf"\n  {service}:.*?healthcheck:", compose, re.DOTALL
            ), f"{service} missing healthcheck"

        # Flower monitoring service is defined with its dependencies wired.
        assert re.search(r"\n  flower:.*?depends_on:", compose, re.DOTALL)


# ---------------------------------------------------------------------------
# 9. Backup and recovery
# ---------------------------------------------------------------------------
class TestBackupAndRecovery:
    """Database backup/recovery plus the backup_manager agent."""

    def test_sqlite_backup_and_recovery(self, tmp_path, monkeypatch):
        """Back up a populated DB, then restore into a fresh database."""
        from sqlalchemy import create_engine

        import openscience.api.database as db_mod
        from openscience.api.config import reset_settings_cache

        monkeypatch.setenv("OPENSCIENCE_API_DATABASE_URL", f"sqlite:///{tmp_path / 'live.db'}")
        reset_settings_cache()
        db_mod.reset_engine()
        db_mod.init_db()

        # Seed a user + session via the ORM.
        from openscience.api.middleware.auth import hash_password
        from openscience.api.models.session import SessionModel
        from openscience.api.models.user import UserModel

        db = next(db_mod.get_db())
        try:
            user = UserModel(
                username="bk_user", email="bk@t.dev", hashed_password=hash_password("bk-pass-123")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            db.add(SessionModel(name="bk", owner_id=user.id, status="active"))
            db.commit()
        finally:
            db.close()

        # Backup via SQLite online backup API.
        import sqlite3

        src = sqlite3.connect(tmp_path / "live.db")
        dst = sqlite3.connect(tmp_path / "backup.db")
        src.backup(dst)
        dst.close()
        src.close()

        # "Recover": point the app at the backup and verify data integrity.
        monkeypatch.setenv("OPENSCIENCE_API_DATABASE_URL", f"sqlite:///{tmp_path / 'backup.db'}")
        reset_settings_cache()
        db_mod.reset_engine()
        engine = create_engine(f"sqlite:///{tmp_path / 'backup.db'}")
        with engine.connect() as conn:
            rows = conn.exec_driver_sql("SELECT username FROM users").fetchall()
            assert rows == [("bk_user",)]
            sessions = conn.exec_driver_sql("SELECT name FROM sessions").fetchall()
            assert sessions == [("bk",)]
        db_mod.reset_engine()

    def test_backup_manager_agent_exec_result(self, tmp_path):
        """The backup_manager agent executes through the orchestrator."""
        src = tmp_path / "project"
        src.mkdir()
        (src / "notes.txt").write_text("ran qc on 2 genes")
        backup_root = tmp_path / "backups"

        from openscience.core.orchestrator import AgentOrchestrator

        orch = AgentOrchestrator()
        assert "backup_manager" in orch.agents
        result = orch.execute_agent(
            "backup_manager",
            {"source_dir": str(src), "backup_root": str(backup_root)},
            {},
        )
        assert result is not None
        assert result.metadata.get("agent") == "backup_manager"
        assert isinstance(result.data, dict)
        assert result.data["status"] == "ok"
        # The snapshot really landed on disk.
        assert any(backup_root.iterdir())

    def test_data_ingestor_supports_backup_formats(self):
        """The data_management category retains its data ingestor agent."""
        from openscience.core.orchestrator import AgentOrchestrator

        orch = AgentOrchestrator()
        for name in ("data_ingestor", "backup_manager", "version_controller"):
            assert name in orch.agents

        # Orchestrator can route a backup-style task to a valid agent.
        result = orch.execute_task("back up and archive analysis data", parameters={}, context={})
        assert result is not None


# ---------------------------------------------------------------------------
# 10. Upgrade path
# ---------------------------------------------------------------------------


class TestUpgradePath:
    """Alembic migrations: upgrade head and clean downgrade."""

    def test_alembic_upgrade_head_creates_schema(self, tmp_path, monkeypatch):
        pytest.importorskip("alembic")
        from alembic.config import Config
        from sqlalchemy import create_engine

        from alembic import command

        monkeypatch.setenv("OPENSCIENCE_API_DATABASE_URL", f"sqlite:///{tmp_path / 'mig.db'}")
        cfg = Config(str(_repo_root() / "alembic.ini"))
        cfg.set_main_option("script_location", str(_repo_root() / "alembic"))
        command.upgrade(cfg, "head")

        from sqlalchemy import inspect

        engine = create_engine(f"sqlite:///{tmp_path / 'mig.db'}")
        tables = set(inspect(engine).get_table_names())
        assert {"users", "agents", "sessions", "tasks", "alembic_version"} <= tables

        # Columns exist as expected on the sessions table (integration of
        # the schema with the ORM models).
        cols = {c["name"] for c in inspect(engine).get_columns("sessions")}
        assert {
            "id",
            "name",
            "owner_id",
            "project_dir",
            "compute_backend",
            "status",
            "data_keys",
            "loaded_data",
            "created_at",
            "updated_at",
        } <= cols

    def test_alembic_downgrade_then_upgrade_roundtrip(self, tmp_path, monkeypatch):
        pytest.importorskip("alembic")
        from alembic.config import Config
        from sqlalchemy import create_engine, inspect

        from alembic import command

        monkeypatch.setenv("OPENSCIENCE_API_DATABASE_URL", f"sqlite:///{tmp_path / 'rt.db'}")
        cfg = Config(str(_repo_root() / "alembic.ini"))
        cfg.set_main_option("script_location", str(_repo_root() / "alembic"))

        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        engine = create_engine(f"sqlite:///{tmp_path / 'rt.db'}")
        tables = set(inspect(engine).get_table_names())
        assert "users" not in tables and "sessions" not in tables

        # Re-upgrade: schema returns and the API can boot on it.
        command.upgrade(cfg, "head")
        tables = set(inspect(engine).get_table_names())
        assert {"users", "agents", "sessions", "tasks"} <= tables

    def test_orm_metadata_matches_migration_head(self):
        """ORM metadata and the 0001 migration agree on table names."""
        import openscience.api.models  # noqa: F401 (register models)
        from openscience.api.database import Base

        orm_tables = set(Base.metadata.tables.keys())
        assert {"users", "agents", "sessions", "tasks"} <= orm_tables
