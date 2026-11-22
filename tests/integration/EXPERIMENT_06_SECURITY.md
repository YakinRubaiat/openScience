# Experiment 06 — Security Audit

**Date:** 2026-11-22 19:53:31 UTC
**Target:** openScience API at `/Users/srubaiat/openScience`
**Overall worst severity:** **HIGH**

## Scope & Method

Ten security controls were exercised against the openScience FastAPI service and core framework:
1. Authentication mechanism
2. JWT token validation
3. Authorization (RBAC)
4. Static security review (bandit)
5. Dependency vulnerability scan (pip-audit)
6. Sandbox isolation
7. File access controls
8. Network egress controls
9. OWASP ZAP baseline scan
10. API input validation

All dynamic tests ran against an isolated SQLite database (`.audit_security.db`) and a TestClient instance of the FastAPI app.

## Findings

| # | Test | Severity | Status |
|---|------|----------|--------|
| T1 | Authentication mechanism | **MEDIUM** | PASS_WITH_NOTES |
| T2a | alg=none rejected | **INFO** | PASS |
| T2 | JWT token validation | **HIGH** | FAIL |
| T3 | Authorization (RBAC) | **MEDIUM** | PASS_WITH_NOTES |
| T4 | Static security review (bandit) | **MEDIUM** | PASS_WITH_NOTES |
| T5 | Dependency vulnerability scan | **INFO** | PASS |
| T6 | Sandbox isolation | **HIGH** | FAIL |
| T7 | File access controls | **INFO** | PASS |
| T8 | Network egress controls | **HIGH** | FAIL |
| T9 | OWASP ZAP scan | **MEDIUM** | SKIP |
| T10 | API input validation | **HIGH** | FAIL |

## Details

### T1 — Authentication mechanism  (MEDIUM)

**Status:** PASS_WITH_NOTES

**Findings:** No account-lockout, no MFA, no password-complexity policy beyond min length 8; No refresh-token rotation; single long-lived access token only

**Recommendation:** Add rate-limit per username, account lockout, MFA (TOTP), refresh-token rotation, and stronger password rules.

### T2a — alg=none rejected  (INFO)

**Status:** PASS

**Findings:** alg=none returned 401

**Recommendation:** 

### T2 — JWT token validation  (HIGH)

**Status:** FAIL

**Findings:** HIGH: API is using the public default SECRET_KEY — any forged token with that key would be accepted in production

**Recommendation:** Rotate SECRET_KEY out of source control; reject alg=none explicitly; consider asymmetric keys (RS256) and per-environment key rotation.

### T3 — Authorization (RBAC)  (MEDIUM)

**Status:** PASS_WITH_NOTES

**Findings:** Registration accepted unexpected extra fields (should be strict); INFO: no admin-only routes exist; `is_admin` flag is defined on the model but never enforced elsewhere

**Recommendation:** Add an admin role & admin-only endpoints; enforce ownership checks on every session-scoped route.

### T4 — Static security review (bandit)  (MEDIUM)

**Status:** PASS_WITH_NOTES

**Findings:** highs=0, mediums=4, lows=7. [MEDIUM] B104 Possible binding to all interfaces. (src/openscience/api/serve.py:13); [MEDIUM] B314 Using xml.etree.ElementTree.fromstring to parse untrusted XML data is known to b (src/openscience/connectors/papers/pubmed.py:147); [MEDIUM] B301 Pickle and modules that wrap it can be unsafe when used to deserialize untrusted (src/openscience/core/session.py:245); [MEDIUM] B314 Using xml.etree.ElementTree.fromstring to parse untrusted XML data is known to b (src/openscience/skills/writing/pubmed.py:45)

**Recommendation:** Tighten bandit config to fail on HIGH severity; review MED findings.

### T5 — Dependency vulnerability scan  (INFO)

**Status:** PASS

**Findings:** pip-audit reported 0 known vulnerabilities.

**Recommendation:** Pin & update affected packages; add pip-audit to CI.

### T6 — Sandbox isolation  (HIGH)

**Status:** FAIL

**Findings:** HIGH: OPENSCIENCE_API_SANDBOX_ENABLED defaults to False — sensitive endpoints run without sandbox

**Recommendation:** Enable sandbox by default in production; wire the approval handler to a real UI; enforce per-task resource caps.

### T7 — File access controls  (INFO)

**Status:** PASS

**Findings:** Traversal and absolute paths blocked at the validator

**Recommendation:** Reject absolute paths at the validator; resolve paths against a configured sandbox root; never let a session touch files outside its project_dir.

### T8 — Network egress controls  (HIGH)

**Status:** FAIL

**Findings:** HIGH: Sandbox does not enforce network egress at the OS/socket level — it only consults the policy flag

**Recommendation:** Run agents in a seccomp/AppArmor/firewalled container; the in-process policy flag is advisory only.

### T9 — OWASP ZAP scan  (MEDIUM)

**Status:** SKIP

**Findings:** OWASP ZAP must run against the *deployed* API outside the audit process to avoid SQLite locking conflicts. Run from a CI worker that can reach the app: `docker run --rm --network host -v $(pwd)/zap:/zap/wrk/:rw ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t http://host.docker.internal:8000 -J zap-report.json -r zap-report.html` Docker is available locally; ZAP was skipped here for isolation, run the command above against the deployed service in CI.

**Recommendation:** Add `zap-baseline.py` (and an authenticated scan) to the CI/CD pipeline; run against the deployed staging service.

### T10 — API input validation  (HIGH)

**Status:** FAIL

**Findings:** FIXED: the global RequestValidationError handler used to 500 on AfterValidator failures because it tried to JSON-serialize the raw ValueError; patched to use jsonable_encoder; Task body echoed raw: {"id":"7d092fd8-9b16-4035-bb1b-385479857ca3","session_id":"22058744-f9ac-4bed-a8f7-c29e5a157598","task_type":"analyze","description":"<script>alert(1)</script>","parameters":{"task":"<script>alert(1)<

**Recommendation:** Keep strict Pydantic models; add a max-body-size middleware; never echo raw user input.

## Recommendations

1. **Rotate secrets.** The default `SECRET_KEY` is checked into source control — move it to a secrets manager before deploying.
2. **Enforce sandboxing by default.** Set `OPENSCIENCE_API_SANDBOX_ENABLED=true` in production.
3. **Harden the JWT layer.** Reject `alg=none` explicitly, consider RS256, add refresh-token rotation, and enforce audience/issuer claims.
4. **Tighten input validation.** Reject absolute paths in `SafeFilePath`; cap request body size; never echo raw input back.
5. **Run security scanners in CI.** Add `bandit --exit-non-zero-on HIGH` and `pip-audit --fail-on HIGH` to the GitHub Actions workflow.
6. **Add ZAP to CI.** Run `zap-baseline.py` against a staging deployment for every release.
7. **RBAC.** There is no admin-only endpoints yet; add an `admin` dependency and apply ownership checks everywhere.
8. **Rate limiting.** `RATE_LIMIT_ENABLED` defaults to true in config, but is disabled in this audit — keep it enabled in production.
