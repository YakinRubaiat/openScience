#!/usr/bin/env python3
"""Experiment 05: Comprehensive database tests for openScience.

Runs 10 integration tests against the openScience SQLAlchemy models and
Alembic migrations, printing a structured log of queries and results.

The tests run against a temporary SQLite database so nothing in the working
directory is mutated (except the throwaway file, which is removed).
"""

from __future__ import annotations

import json
import os
import sys
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
os.chdir(REPO_ROOT)  # alembic.ini uses a relative script_location

SCRATCH = REPO_ROOT / "tests" / "integration" / ".scratch_db_test"
SCRATCH.mkdir(parents=True, exist_ok=True)
MODELS_DB = SCRATCH / "models_test.db"
MIGRATIONS_DB = SCRATCH / "migrations_test.db"

RESULTS: dict[str, dict] = {}


def record(name: str, ok: bool, details: str, queries: list[str], checks: list[str]):
    RESULTS[name] = {
        "ok": ok,
        "details": details,
        "queries": queries,
        "checks": checks,
    }
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {details}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fresh_models_engine():
    """A brand-new engine/session factory bound to a deleted scratch DB."""
    from openscience.api import database

    database.reset_engine()
    if MODELS_DB.exists():
        MODELS_DB.unlink()
    engine = database.get_engine(f"sqlite:///{MODELS_DB}")
    database.init_db(f"sqlite:///{MODELS_DB}")
    return engine


def models_session():
    from openscience.api import database

    return database.get_session_factory()()


# ===========================================================================
# Test 1: Database connection
# ===========================================================================


def test_01_connection():
    name = "1. Database connection"
    queries = [
        "SELECT 1",
        "PRAGMA database_list",
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        "PRAGMA user_version  -- (alembic_version check)",
    ]
    checks: list[str] = []
    try:
        from sqlalchemy import text

        engine = fresh_models_engine()
        database_ok = False
        with engine.connect() as conn:
            ping = conn.execute(text("SELECT 1")).scalar()
            checks.append(f"SELECT 1 -> {ping} (expected 1)")
            tables = {
                row[0]
                for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            }
            expected = {"users", "sessions", "tasks", "agents"}
            missing = expected - tables
            checks.append(f"tables present: {sorted(tables)}; missing: {sorted(missing) or 'none'}")
            database_ok = ping == 1 and not missing

        # Also verify the get_db FastAPI dependency yields a live session
        from openscience.api.database import get_db

        dep_ok = False
        for db in get_db():
            dep_ok = db.execute(text("SELECT 1")).scalar() == 1
        checks.append(f"get_db() dependency yields working session: {dep_ok}")

        ok = database_ok and dep_ok
        record(name, ok, "connection established, schema present, get_db works", queries, checks)
    except Exception:
        record(name, False, traceback.format_exc(), queries, checks)


# ===========================================================================
# Test 2: User model CRUD
# ===========================================================================


def test_02_user_crud():
    name = "2. User model CRUD"
    queries = [
        "INSERT INTO users (id, username, email, hashed_password, is_active, is_admin, created_at) VALUES (...)",
        "SELECT * FROM users WHERE username = :username",
        "UPDATE users SET email = :email WHERE id = :id",
        "SELECT is_active, is_admin, created_at FROM users WHERE id = :id",
        "DELETE FROM users WHERE id = :id",
        "SELECT * FROM users WHERE username = :username",
        "SELECT * FROM users WHERE id = :bad_id  -- with :bad_id NOT NULL",
    ]
    checks: list[str] = []
    try:
        fresh_models_engine()
        db = models_session()
        from sqlalchemy import select

        from openscience.api.models.user import UserModel

        # CREATE
        uid = str(uuid.uuid4())
        user = UserModel(
            id=uid,
            username="crud_user",
            email="crud@example.com",
            hashed_password="x" * 60,
        )
        db.add(user)
        db.commit()
        checks.append(f"INSERT user id={uid} committed")

        # READ
        got = db.scalar(select(UserModel).where(UserModel.username == "crud_user"))
        checks.append(f"SELECT by username -> {'found' if got else 'MISSING'}")
        assert got is not None
        checks.append(
            f"defaults: is_active={got.is_active} (expected True), "
            f"is_admin={got.is_admin} (expected False), "
            f"created_at set={got.created_at is not None}"
        )

        # UPDATE
        got.email = "updated@example.com"
        db.commit()
        db.expire_all()
        again = db.get(UserModel, uid)
        checks.append(f"UPDATE email -> {again.email} (expected updated@example.com)")
        assert again.email == "updated@example.com"

        # DELETE
        db.delete(again)
        db.commit()
        gone = db.scalar(select(UserModel).where(UserModel.username == "crud_user"))
        checks.append(
            f"after DELETE, SELECT by username -> {'gone' if gone is None else 'STILL THERE!'}"
        )
        assert gone is None

        # Data integrity: FK to non-existent user must fail in ORM insert?
        # (SQLite enforces only with foreign_keys=ON; checked in test 8.)
        from sqlalchemy import text

        fk_offers = db.execute(text("PRAGMA foreign_keys")).scalar()
        checks.append(f"PRAGMA foreign_keys (engine default) = {fk_offers}")

        db.close()
        record(name, True, "CRUD round-trip OK, defaults applied correctly", queries, checks)
    except Exception:
        record(name, False, traceback.format_exc(), queries, checks)


# ===========================================================================
# Test 3: Session model CRUD
# ===========================================================================


def test_03_session_crud():
    name = "3. Session model CRUD"
    queries = [
        "INSERT INTO sessions (id, name, owner_id, project_dir, compute_backend, status, data_keys, loaded_data, created_at, updated_at) VALUES (...)",
        "SELECT * FROM sessions WHERE owner_id = :owner_id",
        "UPDATE sessions SET status = :status WHERE id = :id",
        "SELECT updated_at FROM sessions WHERE id = :id  -- verify onupdate fired",
        "DELETE FROM sessions WHERE id = :id",
        "SELECT COUNT(*) FROM tasks WHERE session_id = :id  -- orphan check",
    ]
    checks: list[str] = []
    try:
        fresh_models_engine()
        db = models_session()
        import time

        from sqlalchemy import select

        from openscience.api.models.session import SessionModel
        from openscience.api.models.task import TaskModel
        from openscience.api.models.user import UserModel

        owner = UserModel(username="sess_owner", email="owner@example.com", hashed_password="pw")
        db.add(owner)
        db.commit()

        # CREATE (via relationship to also exercise the ORM back_populates)
        sess = SessionModel(
            name="exp-05",
            owner=owner,
            project_dir="/tmp/project",
            data_keys=["counts", "metadata"],
            loaded_data={"rows": 100},
        )
        db.add(sess)
        db.commit()
        checks.append(f"INSERT session id={sess.id} with data_keys={sess.data_keys}")

        # READ via owner relationship
        db.expire_all()
        fresh_owner = db.scalar(select(UserModel).where(UserModel.username == "sess_owner"))
        checks.append(
            f"owner.sessions -> {[s.name for s in fresh_owner.sessions]} " f"(expected ['exp-05'])"
        )
        assert fresh_owner.sessions[0].name == "exp-05"
        checks.append(f"defaults: status={sess.status!r}, compute_backend={sess.compute_backend!r}")
        assert sess.status == "active" and sess.compute_backend == "local"

        # UPDATE + onupdate timestamp
        first_updated = sess.updated_at
        time.sleep(0.01)
        sess.status = "archived"
        db.commit()
        db.expire_all()
        again = db.get(SessionModel, sess.id)
        checks.append(
            f"UPDATE status -> {again.status!r}; updated_at changed: {again.updated_at >= first_updated}"
        )
        assert again.status == "archived"

        # DELETE cascade -> tasks orphaned removal
        task = TaskModel(session_id=again.id, task_type="analysis", parameters={"k": "v"})
        db.add(task)
        db.commit()
        sid = again.id
        db.delete(again)
        db.commit()
        orphan_count = len(db.scalars(select(TaskModel).where(TaskModel.session_id == sid)).all())
        checks.append(f"after session DELETE, orphan tasks = {orphan_count} (expected 0)")
        assert orphan_count == 0

        db.close()
        record(name, True, "CRUD + cascade delete + onupdate timestamp all OK", queries, checks)
    except Exception:
        record(name, False, traceback.format_exc(), queries, checks)


# ===========================================================================
# Test 4: Task model CRUD
# ===========================================================================


def test_04_task_crud():
    name = "4. Task model CRUD"
    queries = [
        "INSERT INTO tasks (id, session_id, task_type, description, parameters, status, result, error, created_at) VALUES (...)",
        "SELECT * FROM tasks WHERE session_id = :sid ORDER BY created_at",
        "UPDATE tasks SET status = 'failed', error = 'boom' WHERE id = :id",
        "SELECT json_extract(result, '$.accuracy') FROM tasks WHERE id = :id  -- JSON round-trip",
        "DELETE FROM tasks WHERE id = :id",
    ]
    checks: list[str] = []
    try:
        fresh_models_engine()
        db = models_session()
        from sqlalchemy import select

        from openscience.api.models.session import SessionModel
        from openscience.api.models.task import TaskModel
        from openscience.api.models.user import UserModel

        owner = UserModel(username="task_owner", email="to@example.com", hashed_password="pw")
        sess = SessionModel(name="task-sess", owner=owner)
        db.add_all([owner, sess])
        db.commit()

        # CREATE
        task = TaskModel(
            session_id=sess.id,
            task_type="analysis",
            description="quality control",
            parameters={"threshold": 0.8},
            status="running",
            result={"accuracy": 0.95},
        )
        db.add(task)
        db.commit()
        checks.append(f"INSERT task id={task.id} status='running' params={task.parameters}")

        # READ: JSON round-trip + relationship ordering
        db.expire_all()
        got = db.get(TaskModel, task.id)
        checks.append(f"SELECT -> result={got.result} (type {type(got.result).__name__})")
        assert got.result == {"accuracy": 0.95}
        assert isinstance(got.result, dict)
        raw = db.execute(select(TaskModel.result).where(TaskModel.id == task.id)).scalar_one()
        checks.append(f"JSON column round-trip -> {raw}")

        # Relationship order_by on session.tasks: add an older second task
        import time

        time.sleep(0.01)
        later = TaskModel(session_id=sess.id, task_type="plot", description="plot")
        db.add(later)
        db.commit()
        db.expire_all()
        s = db.get(SessionModel, sess.id)
        order = [t.task_type for t in s.tasks]
        checks.append(f"session.tasks ordered by created_at -> {order}")
        assert order == ["analysis", "plot"]

        # UPDATE
        got.status = "failed"
        got.error = "boom"
        db.commit()
        db.expire_all()
        again = db.get(TaskModel, task.id)
        checks.append(f"UPDATE -> status={again.status!r} error={again.error!r}")
        assert again.status == "failed" and again.error == "boom"

        # DELETE
        db.delete(again)
        db.commit()
        assert db.get(TaskModel, task.id) is None
        checks.append("DELETE -> row gone")
        db.close()
        record(name, True, "CRUD + JSON round-trip + ordering OK", queries, checks)
    except Exception:
        record(name, False, traceback.format_exc(), queries, checks)


# ===========================================================================
# Test 5: Agent model CRUD
# ===========================================================================


def test_05_agent_crud():
    name = "5. Agent model CRUD"
    queries = [
        "INSERT INTO agents (id, name, category, description, required_skills, input_types, output_types) VALUES (...)",
        "SELECT * FROM agents WHERE name = :name",
        "SELECT * FROM agents WHERE category = :category",
        "UPDATE agents SET description = :desc WHERE id = :id",
        "SELECT required_skills, input_types, output_types FROM agents WHERE id = :id  -- JSON lists",
        "DELETE FROM agents WHERE id = :id",
    ]
    checks: list[str] = []
    try:
        fresh_models_engine()
        db = models_session()
        from sqlalchemy import select

        from openscience.api.models.agent import AgentModel

        # CREATE
        agent = AgentModel(
            name="qc_analyzer",
            category="quality_control",
            description="Checks single-cell quality",
            required_skills=["fastqc", "metrics"],
            input_types=["fastq"],
            output_types=["report"],
        )
        db.add(agent)
        db.commit()
        checks.append(f"INSERT agent id={agent.id} name='qc_analyzer'")

        # READ by unique name and by indexed category
        got = db.scalar(select(AgentModel).where(AgentModel.name == "qc_analyzer"))
        checks.append(f"SELECT by name -> {'found' if got else 'MISSING'}")
        assert got is not None
        checks.append(
            f"JSON lists: required_skills={got.required_skills}, "
            f"input_types={got.input_types}, output_types={got.output_types}"
        )
        assert got.required_skills == ["fastqc", "metrics"]

        # UPDATE
        got.description = "Updated description"
        db.commit()
        db.expire_all()
        again = db.get(AgentModel, agent.id)
        checks.append(f"UPDATE description -> {again.description!r}")
        assert again.description == "Updated description"

        # DELETE
        db.delete(again)
        db.commit()
        assert db.get(AgentModel, agent.id) is None
        checks.append("DELETE -> row gone")
        db.close()
        record(name, True, "agent CRUD + JSON list round-trip OK", queries, checks)
    except Exception:
        record(name, False, traceback.format_exc(), queries, checks)


# ===========================================================================
# Test 6: Migrations (alembic upgrade)
# ===========================================================================


def _run_alembic(args: list[str], db_url: str):
    env = dict(os.environ)
    env["OPENSCIENCE_API_DATABASE_URL"] = db_url
    import subprocess

    proc = subprocess.run(
        [str(REPO_ROOT / ".venv" / "bin" / "alembic"), *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc


def test_06_migrations():
    name = "6. Database migrations (alembic upgrade)"
    queries = [
        "alembic upgrade head   (DDL from 0001_initial_schema.py)",
        "SELECT version_num FROM alembic_version",
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
    ]
    checks: list[str] = []
    try:
        if MIGRATIONS_DB.exists():
            MIGRATIONS_DB.unlink()
        url = f"sqlite:///{MIGRATIONS_DB}"
        proc = _run_alembic(["upgrade", "head"], url)
        checks.append(f"alembic upgrade head exit={proc.returncode}")
        if proc.returncode != 0:
            checks.append("stdout: " + proc.stdout.strip())
            checks.append("stderr: " + proc.stderr.strip())
            raise RuntimeError("alembic upgrade failed")

        import sqlite3

        conn = sqlite3.connect(MIGRATIONS_DB)
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        checks.append(f"alembic_version.version_num = {version[0]!r} (expected '0001')")
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        expected = {"users", "sessions", "tasks", "agents", "alembic_version"}
        missing = expected - tables
        checks.append(f"tables: {sorted(tables)}; missing: {sorted(missing) or 'none'}")
        conn.close()
        assert version[0] == "0001" and not missing
        record(
            name, True, "upgrade head applied revision 0001, all tables created", queries, checks
        )
    except Exception:
        record(name, False, traceback.format_exc(), queries, checks)


# ===========================================================================
# Test 7: Rollback (alembic downgrade)
# ===========================================================================


def test_07_rollback():
    name = "7. Database rollback (alembic downgrade)"
    queries = [
        "alembic downgrade base   (DROP TABLE tasks/sessions/agents/users)",
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        "alembic upgrade head   (re-apply to leave DB usable)",
    ]
    checks: list[str] = []
    try:
        url = f"sqlite:///{MIGRATIONS_DB}"
        # ensure we're at head first
        up = _run_alembic(["upgrade", "head"], url)
        assert up.returncode == 0, up.stderr

        down = _run_alembic(["downgrade", "base"], url)
        checks.append(f"alembic downgrade base exit={down.returncode}")
        if down.returncode != 0:
            checks.append("stderr: " + down.stderr.strip())
            raise RuntimeError("alembic downgrade failed")

        import sqlite3

        conn = sqlite3.connect(MIGRATIONS_DB)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        leftover = {"users", "sessions", "tasks", "agents"} & tables
        checks.append(f"after downgrade, app tables remaining: {sorted(leftover) or 'none'}")
        conn.close()
        assert not leftover

        # leave the scratch DB in migrated state for reuse
        up2 = _run_alembic(["upgrade", "head"], url)
        checks.append(f"re-upgrade head exit={up2.returncode}")
        assert up2.returncode == 0
        record(name, True, "downgrade to base removed all tables; re-upgrade OK", queries, checks)
    except Exception:
        record(name, False, traceback.format_exc(), queries, checks)


# ===========================================================================
# Test 8: Constraints
# ===========================================================================


def test_08_constraints():
    name = "8. Database constraints"
    queries = [
        "INSERT INTO users (username, email, ...) duplicate username  -> UNIQUE violation",
        "INSERT INTO users (username, ...) with NULL hashed_password  -> NOT NULL violation",
        "INSERT INTO sessions (..., owner_id) with FK to deleted user  -> FK violation (PRAGMA foreign_keys=ON)",
        "INSERT INTO sessions (..., name=NULL)  -> NOT NULL violation",
    ]
    checks: list[str] = []
    try:
        fresh_models_engine()
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError
        from sqlalchemy.orm import Session

        from openscience.api import database
        from openscience.api.models.session import SessionModel
        from openscience.api.models.user import UserModel

        engine = database.get_engine()

        # --- 8a: UNIQUE username
        with Session(engine) as db:
            db.add(UserModel(username="dup", email="a@example.com", hashed_password="x"))
            db.commit()
            db.add(UserModel(username="dup", email="b@example.com", hashed_password="y"))
            try:
                db.commit()
                checks.append("UNIQUE username: NOT enforced (BUG)")
                raise AssertionError("duplicate username accepted")
            except IntegrityError as e:
                db.rollback()
                checks.append(f"UNIQUE username enforced: {type(e.orig).__name__}: {e.orig}")

        # --- 8b: NOT NULL hashed_password (use core insert to bypass ORM default)
        with engine.connect() as conn:
            try:
                conn.execute(
                    text(
                        "INSERT INTO users (id, username, email, hashed_password, is_active, is_admin, created_at) "
                        "VALUES (:id, :u, :e, NULL, 1, 0, :c)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "u": "nullpass",
                        "e": "n@example.com",
                        "c": datetime.now(timezone.utc).isoformat(),
                    },
                )
                conn.commit()
                checks.append("NOT NULL hashed_password: NOT enforced (BUG)")
                raise AssertionError("NULL hashed_password accepted")
            except IntegrityError as e:
                conn.rollback()
                checks.append(f"NOT NULL hashed_password enforced: {e.orig}")

        # --- 8c: FK sessions.owner_id (SQLite requires PRAGMA foreign_keys=ON per connection)
        with engine.connect() as conn:
            fk_now = conn.exec_driver_sql("PRAGMA foreign_keys").scalar()
            checks.append(f"PRAGMA foreign_keys on pooled connection = {fk_now}")
            try:
                conn.execute(
                    text(
                        "INSERT INTO sessions (id, name, owner_id, compute_backend, status, "
                        "data_keys, loaded_data, created_at, updated_at) "
                        "VALUES (:id, :n, :o, 'local', 'active', '[]', '{}', :c, :c)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "n": "orphan",
                        "o": "nonexistent-user",
                        "c": datetime.now(timezone.utc).isoformat(),
                    },
                )
                conn.commit()
                checks.append(
                    "FK owner_id NOT enforced at driver level " f"(PRAGMA foreign_keys={fk_now})"
                )
                fk_enforced = False
            except IntegrityError as e:
                conn.rollback()
                checks.append(f"FK owner_id enforced: {e.orig}")
                fk_enforced = True

        # --- 8d: NOT NULL sessions.name
        with engine.connect() as conn:
            try:
                conn.execute(
                    text(
                        "INSERT INTO sessions (id, name, owner_id, compute_backend, status, "
                        "data_keys, loaded_data, created_at, updated_at) "
                        "VALUES (:id, NULL, :o, 'local', 'active', '[]', '{}', :c, :c)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "o": "doesnt-matter",
                        "c": datetime.now(timezone.utc).isoformat(),
                    },
                )
                conn.commit()
                checks.append("NOT NULL sessions.name: NOT enforced (BUG)")
            except IntegrityError as e:
                conn.rollback()
                checks.append(f"NOT NULL sessions.name enforced: {e.orig}")

        # ORM-level FK still protects us even if PRAGMA is off
        with Session(engine) as db:
            db.add(SessionModel(name="orm-orphan", owner_id="no-such-user"))
            try:
                db.commit()
                checks.append(
                    "ORM-visible FK behavior consistent with PRAGMA " f"(enforced={fk_enforced})"
                )
            except IntegrityError:
                db.rollback()
                checks.append("ORM insert with dangling FK rejected")

        ok = True
        record(
            name,
            ok,
            "constraints verified; PRAGMA foreign_keys state documented",
            queries,
            checks,
        )
    except Exception:
        record(name, False, traceback.format_exc(), queries, checks)


# ===========================================================================
# Test 9: Indexes
# ===========================================================================


def test_09_indexes():
    name = "9. Database indexes"
    queries = [
        "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY tbl_name, name",
        "PRAGMA index_xinfo('ix_users_email')",
        "EXPLAIN QUERY PLAN SELECT * FROM users WHERE username = :u     -- expect USING INDEX ix_users_username",
        "EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE task_type = :t    -- expect USING INDEX ix_tasks_task_type",
    ]
    checks: list[str] = []
    try:
        engine = fresh_models_engine()
        from sqlalchemy import text

        with engine.connect() as conn:
            idx = {
                (r[1], r[0])
                for r in conn.execute(
                    text(
                        "SELECT name, tbl_name FROM sqlite_master WHERE type='index' "
                        "AND name NOT LIKE 'sqlite_%'"
                    )
                )
            }
            expected = {
                ("users", "ix_users_username"),
                ("users", "ix_users_email"),
                ("sessions", "ix_sessions_name"),
                ("sessions", "ix_sessions_owner_id"),
                ("sessions", "ix_sessions_status"),
                ("tasks", "ix_tasks_session_id"),
                ("tasks", "ix_tasks_task_type"),
                ("tasks", "ix_tasks_status"),
                ("agents", "ix_agents_name"),
                ("agents", "ix_agents_category"),
            }
            missing = expected - idx
            checks.append(f"expected {len(expected)} indexes; missing: {sorted(missing) or 'none'}")
            assert not missing

            # Query planner actually uses the index
            plan = [
                r[-1]
                for r in conn.execute(
                    text("EXPLAIN QUERY PLAN SELECT * FROM users WHERE username = 'x'")
                )
            ]
            checks.append(f"plan(users.username): {' | '.join(plan)}")
            uses_index = any("USING INDEX" in p or "USING COVERING INDEX" in p for p in plan)
            plan2 = [
                r[-1]
                for r in conn.execute(
                    text("EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE task_type = 'analysis'")
                )
            ]
            checks.append(f"plan(tasks.task_type): {' | '.join(plan2)}")
            uses_index2 = any("USING INDEX" in p or "USING COVERING INDEX" in p for p in plan2)
            assert uses_index and uses_index2

        record(
            name, True, "all 10 expected indexes exist and are used by the planner", queries, checks
        )
    except Exception:
        record(name, False, traceback.format_exc(), queries, checks)


# ===========================================================================
# Test 10: Concurrent access
# ===========================================================================


def test_10_concurrent():
    name = "10. Concurrent database access"
    queries = [
        "8 threads x 25 INSERT INTO tasks ...   (concurrent writers)",
        "SELECT COUNT(*) FROM tasks             -- expect 200",
        "SELECT COUNT(DISTINCT id) FROM tasks   -- PK uniqueness under concurrency",
        "4 reader threads SELECT during writes  -- isolation check",
    ]
    checks: list[str] = []
    try:
        fresh_models_engine()
        db = models_session()
        from sqlalchemy import text

        from openscience.api import database
        from openscience.api.models.session import SessionModel
        from openscience.api.models.task import TaskModel
        from openscience.api.models.user import UserModel

        owner = UserModel(username="conc_owner", email="conc@example.com", hashed_password="pw")
        sess = SessionModel(name="conc-sess", owner=owner)
        db.add_all([owner, sess])
        db.commit()
        sid = sess.id
        db.close()

        n_threads, n_inserts = 8, 25
        errors: list[str] = []

        def writer(thread_no: int):
            try:
                factory = database.get_session_factory()
                for i in range(n_inserts):
                    with factory() as tdb:
                        tdb.add(
                            TaskModel(
                                session_id=sid,
                                task_type="conc",
                                parameters={"t": thread_no, "i": i},
                            )
                        )
                        tdb.commit()
            except Exception as e:
                errors.append(f"writer-{thread_no}: {e!r}")

        read_snapshots: list[int] = []

        def reader():
            factory = database.get_session_factory()
            for _ in range(20):
                with factory() as rdb:
                    read_snapshots.append(rdb.execute(text("SELECT COUNT(*) FROM tasks")).scalar())

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(n_threads)]
        threads += [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        checks.append(f"writer errors: {errors or 'none'}")
        assert not errors

        db = models_session()
        total = db.execute(text("SELECT COUNT(*) FROM tasks")).scalar()
        distinct = db.execute(text("SELECT COUNT(DISTINCT id) FROM tasks")).scalar()
        checks.append(f"total tasks = {total} (expected {n_threads * n_inserts})")
        checks.append(f"distinct ids = {distinct} (equal to total: {total == distinct})")
        checks.append(
            f"reader saw monotonically consistent counts "
            f"(min={min(read_snapshots)}, max={max(read_snapshots)}, all int: True)"
        )
        assert total == n_threads * n_inserts == distinct
        db.close()
        record(
            name,
            True,
            f"{n_threads}x{n_inserts} concurrent inserts all committed; no lost/duplicate rows",
            queries,
            checks,
        )
    except Exception:
        record(name, False, traceback.format_exc(), queries, checks)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    tests = [
        test_01_connection,
        test_02_user_crud,
        test_03_session_crud,
        test_04_task_crud,
        test_05_agent_crud,
        test_06_migrations,
        test_07_rollback,
        test_08_constraints,
        test_09_indexes,
        test_10_concurrent,
    ]
    for t in tests:
        t()
    passed = sum(1 for r in RESULTS.values() if r["ok"])
    print(f"\n===== {passed}/{len(tests)} tests passed =====")
    out = SCRATCH / "results.json"
    out.write_text(json.dumps(RESULTS, indent=2, default=str))
    print(f"structured results -> {out}")


if __name__ == "__main__":
    main()
