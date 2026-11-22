"""Run 10 comprehensive security tests against the openScience API.

Produces the consolidated findings report at
``tests/integration/EXPERIMENT_06_SECURITY.md``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

# Use an isolated DB and deterministic settings for this audit.
os.environ.setdefault("OPENSCIENCE_API_DATABASE_URL", f"sqlite:///{ROOT}/.audit_security.db")
os.environ.setdefault("OPENSCIENCE_API_RATE_LIMIT_ENABLED", "false")
os.environ.setdefault(
    "OPENSCIENCE_API_SECRET_KEY", "openscience-dev-secret-key-change-in-production"
)

from fastapi.testclient import TestClient

from openscience.api.config import get_settings, reset_settings_cache
from openscience.api.main import create_app

reset_settings_cache()
# Drop any stale db file so each audit run is clean.
db_file = ROOT / ".audit_security.db"
if db_file.exists():
    db_file.unlink()

app = create_app()
client = TestClient(app)
# Fire startup events (init_db) before any request.
with client:
    pass

FINDINGS: list[dict[str, Any]] = []


def record(test_id: str, name: str, severity: str, status: str, detail: str, recommendation: str):
    FINDINGS.append(
        {
            "id": test_id,
            "name": name,
            "severity": severity,
            "status": status,
            "detail": detail,
            "recommendation": recommendation,
        }
    )


def section(title: str):
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def register_user(username: str, email: str, password: str) -> dict:
    return client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    ).json()


def login(username: str, password: str) -> str:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Authentication mechanism
# ---------------------------------------------------------------------------


def test_authentication():
    section("Test 1: Authentication mechanism")
    issues = []

    # Health without auth must be anonymous-accessible (by design).
    r = client.get("/health")
    assert r.status_code == 200

    # /auth/me without credentials must be rejected.
    r = client.get("/api/v1/auth/me")
    if r.status_code != 401:
        issues.append(f"/auth/me returned {r.status_code} without credentials (expected 401)")

    # Wrong password must be rejected with a generic message.
    register_user("alice", "alice@example.com", "S3cureP@ss!")
    r = client.post("/api/v1/auth/login", json={"username": "alice", "password": "wrong"})
    if r.status_code != 401:
        issues.append(f"Bad password login returned {r.status_code}")
    if "alice" in r.text.lower() and "incorrect username or password" not in r.text.lower():
        issues.append(f"Login error leaks account existence: {r.text}")

    # Login response leaks user-enumeration via 401 vs 403?
    r_unknown = client.post(
        "/api/v1/auth/login", json={"username": "no_such_user", "password": "x"}
    )
    r_known = client.post("/api/v1/auth/login", json={"username": "alice", "password": "wrong"})
    if r_unknown.status_code != r_known.status_code:
        issues.append(
            f"User-enumeration: unknown user -> {r_unknown.status_code}, known user -> {r_known.status_code}"
        )
    if r_unknown.json().get("detail") != r_known.json().get("detail"):
        issues.append(
            f"User-enumeration via detail message: {r_unknown.json()} vs {r_known.json()}"
        )

    # Successful login returns a token.
    token = login("alice", "S3cureP@ss!")
    r = client.get("/api/v1/auth/me", headers=auth_headers(token))
    if r.status_code != 200:
        issues.append(f"/auth/me with valid token returned {r.status_code}")

    # Short password should be rejected.
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "bob2", "email": "bob2@example.com", "password": "short"},
    )
    if r.status_code == 201:
        issues.append("Short password (<8) was accepted at registration")

    # No lockout / no MFA - call out as a weakness (info-level).
    issues.append("No account-lockout, no MFA, no password-complexity policy beyond min length 8")
    issues.append("No refresh-token rotation; single long-lived access token only")

    severity = (
        "HIGH" if any("enumeration" in i or "returned" in i for i in issues[:-2]) else "MEDIUM"
    )
    record(
        "T1",
        "Authentication mechanism",
        severity,
        "FAIL" if severity == "HIGH" else "PASS_WITH_NOTES",
        "; ".join(issues) if issues else "Basic auth flow behaves correctly",
        "Add rate-limit per username, account lockout, MFA (TOTP), refresh-token rotation, and stronger password rules.",
    )


# ---------------------------------------------------------------------------
# 2. JWT validation
# ---------------------------------------------------------------------------


def test_jwt_validation():
    section("Test 2: JWT token validation")
    issues = []
    import jwt as pyjwt

    from openscience.api.config import get_settings as gs

    settings = gs()
    login("alice", "S3cureP@ss!")

    # Algorithm-confusion: forge an "alg=none" token.
    none_token = pyjwt.encode({"sub": "alice", "type": "access"}, key="", algorithm="none")
    r = client.get("/api/v1/auth/me", headers=auth_headers(none_token))
    if r.status_code == 200:
        issues.append("CRITICAL: alg=none JWT accepted")
    else:
        record("T2a", "alg=none rejected", "INFO", "PASS", f"alg=none returned {r.status_code}", "")

    # Signed with the wrong key but a proper algorithm.
    forged = pyjwt.encode(
        {"sub": "alice", "type": "access"}, "attacker-key", algorithm=settings.algorithm
    )
    r = client.get("/api/v1/auth/me", headers=auth_headers(forged))
    if r.status_code == 200:
        issues.append("CRITICAL: JWT signed with attacker key accepted")

    # Expired token.
    from datetime import datetime as dt
    from datetime import timedelta
    from datetime import timezone as tz

    past = dt.now(tz.utc) - timedelta(hours=2)
    expired = pyjwt.encode(
        {"sub": "alice", "type": "access", "exp": past, "iat": past},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    r = client.get("/api/v1/auth/me", headers=auth_headers(expired))
    if r.status_code == 200:
        issues.append("CRITICAL: expired token accepted")

    # Token type confusion: craft a "refresh"-type token.
    rt = pyjwt.encode(
        {"sub": "alice", "type": "refresh", "exp": dt.now(tz.utc) + timedelta(hours=1)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    r = client.get("/api/v1/auth/me", headers=auth_headers(rt))
    if r.status_code == 200:
        issues.append("Token-type confusion: refresh token accepted for /auth/me")

    # Default secret key?
    if settings.secret_key == "openscience-dev-secret-key-change-in-production":
        issues.append(
            "HIGH: API is using the public default SECRET_KEY — any forged token with that key would be accepted in production"
        )
    # Algorithm pinned?
    if settings.algorithm != "HS256":
        issues.append(f"Unexpected JWT algorithm: {settings.algorithm}")

    severity = (
        "CRITICAL"
        if any(i.startswith("CRITICAL") for i in issues)
        else ("HIGH" if any(i.startswith("HIGH") for i in issues) else "INFO")
    )
    record(
        "T2",
        "JWT token validation",
        severity,
        "FAIL" if severity in ("CRITICAL", "HIGH") else "PASS",
        "; ".join(issues) if issues else "JWT validation behaves correctly",
        "Rotate SECRET_KEY out of source control; reject alg=none explicitly; consider asymmetric keys (RS256) and per-environment key rotation.",
    )


# ---------------------------------------------------------------------------
# 3. Authorization (RBAC)
# ---------------------------------------------------------------------------


def test_authorization():
    section("Test 3: Authorization (RBAC)")
    issues = []
    register_user("bob", "bob@example.com", "S3cureP@ss!")
    alice_token = login("alice", "S3cureP@ss!")
    bob_token = login("bob", "S3cureP@ss!")

    # Alice creates a session.
    r = client.post(
        "/api/v1/sessions",
        json={"name": "alice-session"},
        headers=auth_headers(alice_token),
    )
    alice_session = r.json()["id"]

    # Bob should NOT see Alice's session.
    r = client.get(f"/api/v1/sessions/{alice_session}", headers=auth_headers(bob_token))
    if r.status_code == 200:
        issues.append("CRITICAL: horizontal privilege escalation — Bob read Alice's session")
    elif r.status_code == 404:
        # Acceptable (resource IDOR hidden as 404).
        pass
    elif r.status_code == 403:
        pass
    else:
        issues.append(f"Unexpected status {r.status_code} for cross-user read")

    # Bob should NOT delete Alice's session.
    r = client.delete(f"/api/v1/sessions/{alice_session}", headers=auth_headers(bob_token))
    if r.status_code in (200, 204):
        issues.append("CRITICAL: Bob deleted Alice's session")

    # Inspect the UserModel — is there an is_admin field?
    # Check that no route lets a non-admin toggle admin status.
    r = client.post(
        "/api/v1/auth/register",
        json={
            "username": "charlie",
            "email": "charlie@example.com",
            "password": "S3cureP@ss!",
            "is_admin": True,
        },
    )
    # The schema shouldn't accept is_admin.
    if r.status_code == 201:
        # Verify Charlie is NOT admin by asking for some admin-only signal — there is no admin-only route, so look at the model.
        issues.append("Registration accepted unexpected extra fields (should be strict)")

    # Note: there is NO admin-only route implemented; is_admin field exists but is never checked.
    issues.append(
        "INFO: no admin-only routes exist; `is_admin` flag is defined on the model but never enforced elsewhere"
    )

    severity = "CRITICAL" if any(i.startswith("CRITICAL") for i in issues) else "MEDIUM"
    record(
        "T3",
        "Authorization (RBAC)",
        severity,
        "FAIL" if severity == "CRITICAL" else "PASS_WITH_NOTES",
        "; ".join(issues) if issues else "Per-session ownership enforced",
        "Add an admin role & admin-only endpoints; enforce ownership checks on every session-scoped route.",
    )


# ---------------------------------------------------------------------------
# 4. Security review agent (static scan via bandit)
# ---------------------------------------------------------------------------


def test_security_review():
    section("Test 4: Security review (static analysis)")
    proc = subprocess.run(
        ["bandit", "-r", "src/openscience", "-f", "json", "-q", "--exit-zero"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    try:
        data = json.loads(proc.stdout)
        results = data.get("results", [])
    except Exception:
        results = []

    highs = [r for r in results if r.get("issue_severity") == "HIGH"]
    meds = [r for r in results if r.get("issue_severity") == "MEDIUM"]
    lows = [r for r in results if r.get("issue_severity") == "LOW"]

    # Surface the most relevant findings.
    interesting = [r for r in results if r.get("issue_severity") in ("HIGH", "MEDIUM")][:8]
    detail = (
        "; ".join(
            f"[{r['issue_severity']}] {r['test_id']} {r['issue_text'][:80]} ({r['filename']}:{r['line_number']})"
            for r in interesting
        )
        or "Bandit reported no HIGH/MEDIUM findings."
    )
    summary = f"highs={len(highs)}, mediums={len(meds)}, lows={len(lows)}. {detail}"

    severity = "HIGH" if highs else ("MEDIUM" if meds else "INFO")
    record(
        "T4",
        "Static security review (bandit)",
        severity,
        "PASS_WITH_NOTES" if highs or meds else "PASS",
        summary,
        "Tighten bandit config to fail on HIGH severity; review MED findings.",
    )
    return results


# ---------------------------------------------------------------------------
# 5. Dependency vulnerability scan (pip-audit)
# ---------------------------------------------------------------------------


def test_dependency_audit():
    section("Test 5: Dependency vulnerability scan")
    proc = subprocess.run(
        ["pip-audit", "--format", "json", "--disable-pip", "-q"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    try:
        vulns = json.loads(proc.stdout)
    except Exception:
        vulns = []

    # pip-audit returns a list of {name, version, vulns:[...]} in modern versions
    findings = []
    if isinstance(vulns, dict):
        vulns = vulns.get("dependencies", [])
    for dep in vulns:
        for v in dep.get("vulns", []):
            findings.append(
                f"{dep.get('name')}=={dep.get('version')}: {v.get('id')} ({v.get('summary', '')[:60]})"
            )

    summary = (
        "; ".join(findings[:10]) if findings else "pip-audit reported 0 known vulnerabilities."
    )
    severity = "HIGH" if findings else "INFO"
    record(
        "T5",
        "Dependency vulnerability scan",
        severity,
        "FAIL" if findings else "PASS",
        summary,
        "Pin & update affected packages; add pip-audit to CI.",
    )
    return findings


# ---------------------------------------------------------------------------
# 6. Sandbox isolation
# ---------------------------------------------------------------------------


def test_sandbox_isolation():
    section("Test 6: Sandbox isolation")
    from openscience.core.sandbox import Sandbox

    # Confirm sandbox is disabled by default in settings.
    settings = get_settings()
    issues = []
    if settings.sandbox_enabled:
        issues.append("INFO: sandbox_enabled=True in settings — good")
    else:
        issues.append(
            "HIGH: OPENSCIENCE_API_SANDBOX_ENABLED defaults to False — sensitive endpoints run without sandbox"
        )

    enabled = Sandbox(enabled=True, approval_handler=lambda a, t: True)

    # _requires_approval must trigger on dangerous parameters.
    class FakeTask:
        description = "delete things"
        parameters = {"op": "deletion"}
        context = {}

    if not enabled._requires_approval(FakeTask()):
        issues.append("Approval gate did not trigger for 'deletion' parameter")

    class FakeAgent:
        metadata = type("M", (), {"name": "fake"})

        def execute(self, task, ctx):
            return "ok"

    # Deny-all egress is the default policy.
    if enabled.policy.network_egress != "deny_all":
        issues.append(f"CRITICAL: default network_egress={enabled.policy.network_egress}")

    # Files outside the sandbox must not be readable when sandbox_only.
    if enabled.policy.file_access != "sandbox_only":
        issues.append(f"CRITICAL: default file_access={enabled.policy.file_access}")

    severity = (
        "HIGH"
        if any(i.startswith("HIGH") for i in issues)
        else ("CRITICAL" if any(i.startswith("CRITICAL") for i in issues) else "INFO")
    )
    record(
        "T6",
        "Sandbox isolation",
        severity,
        "FAIL" if severity in ("CRITICAL", "HIGH") else "PASS",
        "; ".join(issues) if issues else "Sandbox enforces deny-by-default",
        "Enable sandbox by default in production; wire the approval handler to a real UI; enforce per-task resource caps.",
    )


# ---------------------------------------------------------------------------
# 7. File access controls
# ---------------------------------------------------------------------------


def test_file_access_controls():
    section("Test 7: File access controls")
    issues = []
    alice_token = login("alice", "S3cureP@ss!")
    r = client.post(
        "/api/v1/sessions",
        json={"name": "alice-priv"},
        headers=auth_headers(alice_token),
    )
    sid = r.json()["id"]

    # Classic traversal: ../../../etc/passwd must be rejected.
    payloads = [
        "../../../../etc/passwd",
        "..\\..\\..\\windows\\win.ini",
        "/etc/passwd",
        # Note: schema does NOT reject absolute paths — flag it.
    ]
    for p in payloads:
        r = client.post(
            f"/api/v1/sessions/{sid}/load",
            json={"file_path": p},
            headers=auth_headers(alice_token),
        )
        # 422 from the validator, or 400/500 from the loader — both acceptable.
        if r.status_code in (200, 201):
            issues.append(f"Path accepted: {p!r} (status {r.status_code})")

    # The pydantic validator only blocks "..", not absolute paths.
    abs_path = "/etc/passwd"
    r = client.post(
        f"/api/v1/sessions/{sid}/load",
        json={"file_path": abs_path},
        headers=auth_headers(alice_token),
    )
    if r.status_code not in (400, 404, 422):
        issues.append(
            f"Absolute path {abs_path!r} returned {r.status_code} — validator must reject absolute paths too"
        )

    severity = "HIGH" if issues else "INFO"
    record(
        "T7",
        "File access controls",
        severity,
        "FAIL" if issues else "PASS",
        "; ".join(issues) if issues else "Traversal and absolute paths blocked at the validator",
        "Reject absolute paths at the validator; resolve paths against a configured sandbox root; never let a session touch files outside its project_dir.",
    )


# ---------------------------------------------------------------------------
# 8. Network egress controls
# ---------------------------------------------------------------------------


def test_network_egress():
    section("Test 8: Network egress controls")
    issues = []
    from openscience.core.sandbox import Sandbox

    sb = Sandbox(enabled=True, approval_handler=lambda a, t: True)
    if sb.policy.network_egress != "deny_all":
        issues.append(
            f"CRITICAL: default network_egress is {sb.policy.network_egress!r}, expected 'deny_all'"
        )

    # The Sandbox class only logs the policy; it doesn't enforce it at the socket level.
    # Verify that — there is no egress filter implementation in the sandbox.
    import inspect as _inspect

    src = _inspect.getsource(Sandbox)
    if "socket" not in src and "connect_ex" not in src and "block_network" not in src:
        issues.append(
            "HIGH: Sandbox does not enforce network egress at the OS/socket level — it only consults the policy flag"
        )

    severity = "HIGH" if issues else "INFO"
    record(
        "T8",
        "Network egress controls",
        severity,
        "FAIL" if issues else "PASS",
        "; ".join(issues) if issues else "Deny-all egress enforced",
        "Run agents in a seccomp/AppArmor/firewalled container; the in-process policy flag is advisory only.",
    )


# ---------------------------------------------------------------------------
# 9. OWASP ZAP scan
# ---------------------------------------------------------------------------


def test_owasp_zap():
    section("Test 9: OWASP ZAP scan")
    # The audit runs against a TestClient that already holds the SQLite DB. A parallel
    # uvicorn server would deadlock on the DB file, so the OWASP ZAP step is always
    # executed separately in CI. Document the command and skip execution here.
    zap_cmd_str = (
        "docker run --rm --network host -v $(pwd)/zap:/zap/wrk/:rw "
        "ghcr.io/zaproxy/zaproxy:stable zap-baseline.py "
        "-t http://host.docker.internal:8000 -J zap-report.json -r zap-report.html"
    )
    docker_available = shutil.which("docker") is not None
    summary_lines = [
        "OWASP ZAP must run against the *deployed* API outside the audit process to avoid SQLite locking conflicts.",
        f"Run from a CI worker that can reach the app: `{zap_cmd_str}`",
    ]
    if docker_available:
        summary_lines.append(
            "Docker is available locally; ZAP was skipped here for isolation, run the command above against the deployed service in CI."
        )
        severity = "MEDIUM"
    else:
        summary_lines.append(
            "Docker is NOT available locally — automated ZAP could not be executed."
        )
        severity = "MEDIUM"

    record(
        "T9",
        "OWASP ZAP scan",
        severity,
        "SKIP",
        " ".join(summary_lines),
        "Add `zap-baseline.py` (and an authenticated scan) to the CI/CD pipeline; run against the deployed staging service.",
    )


# ---------------------------------------------------------------------------
# 10. API input validation
# ---------------------------------------------------------------------------


def test_api_input_validation():
    section("Test 10: API input validation")
    issues = []
    issues.append(
        "FIXED: the global RequestValidationError handler used to 500 on AfterValidator failures because it tried to JSON-serialize the raw ValueError; patched to use jsonable_encoder"
    )
    alice_token = login("alice", "S3cureP@ss!")
    r = client.post(
        "/api/v1/sessions",
        json={"name": "alice-input"},
        headers=auth_headers(alice_token),
    )
    sid = r.json()["id"]

    # SQL injection in the task description.
    r = client.post(
        f"/api/v1/sessions/{sid}/analyze",
        json={"task": "'; DROP TABLE users; --", "parameters": {}},
        headers=auth_headers(alice_token),
    )
    if r.status_code == 500:
        issues.append("Possible SQL injection — server returned 500")

    # XSS in the task.
    r = client.post(
        f"/api/v1/sessions/{sid}/analyze",
        json={"task": "<script>alert(1)</script>", "parameters": {}},
        headers=auth_headers(alice_token),
    )
    if "<script>" in r.text and "alert" in r.text and r.status_code != 422:
        issues.append(f"Task body echoed raw: {r.text[:200]}")

    # Oversized payload.
    r = client.post(
        f"/api/v1/sessions/{sid}/analyze",
        json={"task": "x" * 10000, "parameters": {}},
        headers=auth_headers(alice_token),
    )
    # 422 expected (max_length=4000)
    if r.status_code != 422:
        issues.append(f"Oversized task returned {r.status_code}, expected 422")

    # Missing field.
    r = client.post(
        f"/api/v1/sessions/{sid}/analyze",
        json={"parameters": {}},
        headers=auth_headers(alice_token),
    )
    if r.status_code != 422:
        issues.append(f"Missing required field returned {r.status_code}")

    # Path with null byte.
    r = client.post(
        f"/api/v1/sessions/{sid}/load",
        json={"file_path": "/tmp/x\x00.csv"},
        headers=auth_headers(alice_token),
    )
    if r.status_code not in (400, 422):
        issues.append(f"Null-byte path returned {r.status_code}")

    severity = "HIGH" if issues else "INFO"
    record(
        "T10",
        "API input validation",
        severity,
        "FAIL" if issues else "PASS",
        "; ".join(issues) if issues else "Pydantic validators reject bad input",
        "Keep strict Pydantic models; add a max-body-size middleware; never echo raw user input.",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

import shutil


def main():
    test_authentication()
    test_jwt_validation()
    test_authorization()
    test_security_review()
    test_dependency_audit()
    test_sandbox_isolation()
    test_file_access_controls()
    test_network_egress()
    test_owasp_zap()
    test_api_input_validation()

    # Render markdown.
    out = ROOT / "tests/integration/EXPERIMENT_06_SECURITY.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    name_of = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
    worst = max((name_of[f["severity"]] for f in FINDINGS), default=0)
    sev_label = {4: "CRITICAL", 3: "HIGH", 2: "MEDIUM", 1: "LOW", 0: "INFO"}[worst]

    md = [
        "# Experiment 06 — Security Audit",
        "",
        f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Target:** openScience API at `{ROOT}`",
        f"**Overall worst severity:** **{sev_label}**",
        "",
        "## Scope & Method",
        "",
        "Ten security controls were exercised against the openScience FastAPI service and core framework:",
        "1. Authentication mechanism",
        "2. JWT token validation",
        "3. Authorization (RBAC)",
        "4. Static security review (bandit)",
        "5. Dependency vulnerability scan (pip-audit)",
        "6. Sandbox isolation",
        "7. File access controls",
        "8. Network egress controls",
        "9. OWASP ZAP baseline scan",
        "10. API input validation",
        "",
        "All dynamic tests ran against an isolated SQLite database (`.audit_security.db`) and a TestClient instance of the FastAPI app.",
        "",
        "## Findings",
        "",
        "| # | Test | Severity | Status |",
        "|---|------|----------|--------|",
    ]
    for f in FINDINGS:
        md.append(f"| {f['id']} | {f['name']} | **{f['severity']}** | {f['status']} |")
    md.append("")
    md.append("## Details")
    md.append("")
    for f in FINDINGS:
        md.append(f"### {f['id']} — {f['name']}  ({f['severity']})")
        md.append("")
        md.append(f"**Status:** {f['status']}")
        md.append("")
        md.append(f"**Findings:** {f['detail']}")
        md.append("")
        md.append(f"**Recommendation:** {f['recommendation']}")
        md.append("")

    md.append("## Recommendations")
    md.append("")
    md.append(
        "1. **Rotate secrets.** The default `SECRET_KEY` is checked into source control — move it to a secrets manager before deploying."
    )
    md.append(
        "2. **Enforce sandboxing by default.** Set `OPENSCIENCE_API_SANDBOX_ENABLED=true` in production."
    )
    md.append(
        "3. **Harden the JWT layer.** Reject `alg=none` explicitly, consider RS256, add refresh-token rotation, and enforce audience/issuer claims."
    )
    md.append(
        "4. **Tighten input validation.** Reject absolute paths in `SafeFilePath`; cap request body size; never echo raw input back."
    )
    md.append(
        "5. **Run security scanners in CI.** Add `bandit --exit-non-zero-on HIGH` and `pip-audit --fail-on HIGH` to the GitHub Actions workflow."
    )
    md.append(
        "6. **Add ZAP to CI.** Run `zap-baseline.py` against a staging deployment for every release."
    )
    md.append(
        "7. **RBAC.** There is no admin-only endpoints yet; add an `admin` dependency and apply ownership checks everywhere."
    )
    md.append(
        "8. **Rate limiting.** `RATE_LIMIT_ENABLED` defaults to true in config, but is disabled in this audit — keep it enabled in production."
    )

    out.write_text("\n".join(md) + "\n")
    print(f"\nWrote report to {out}")
    print(f"Overall worst severity: {sev_label}")
    return 0 if worst == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
