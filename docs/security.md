---
layout: default
title: Security Policies
nav_order: 9
description: "Security architecture, policies, and best practices"
---

# Security Policies

openScience implements defense-in-depth to protect data, prevent unauthorized access, and ensure responsible AI use in scientific research.

---

## Security Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Human Approval Broker                                    │
│    Gates deletions, external code exec, network egress     │
├─────────────────────────────────────────────────────────────┤
│ 2. OS-Level Sandbox                                         │
│    Deny-by-default network & filesystem                    │
├─────────────────────────────────────────────────────────────┤
│ 3. Encrypted Credentials                                    │
│    System keyring (Keychain, Secret Service, …)            │
├─────────────────────────────────────────────────────────────┤
│ 4. Biosecurity Safeguards                                   │
│    Dual-use research screening                              │
├─────────────────────────────────────────────────────────────┤
│ 5. Audit Logging                                            │
│    Full provenance with timestamps                          │
├─────────────────────────────────────────────────────────────┤
│ 6. Access Control                                           │
│    API keys & role-based permissions                        │
└─────────────────────────────────────────────────────────────┘
```

---

## OS-Level Sandbox

The sandbox enforces **deny-by-default** policies for every agent operation.

### Network policies

| Policy | Behavior | Use |
|--------|----------|-----|
| `deny_all` | All egress blocked | Untrusted code |
| `allowlist` (default) | Listed hosts only | Research pipelines |
| `permissive` | Open internet | Local dev only |

Configure in `openscience.yaml`:

```yaml
sandbox:
  network_policy: allowlist
  allowed_hosts:
    - pubmed.ncbi.nlm.nih.gov
    - api.semanticscholar.org
    - eutils.ncbi.nlm.nih.gov
```

**Per-connector scoping**: each database connector is granted access to *only* its own base URL. A PubMed connector cannot reach ChEMBL; a compromised agent cannot pivot.

### Filesystem policies

```yaml
sandbox:
  file_system:
    read:
      - data/raw
      - reference/
    write:
      - data/processed
      - results/
      - figures/
```

`data/raw` is **read-only** — accidental overwrites of source data are impossible.

### Human approval broker

Certain operations trigger an interactive approval prompt:

| Operation | Why it needs approval |
|-----------|----------------------|
| File deletion | Irreversible |
| External code execution | Arbitrary risk |
| Network egress beyond allowlist | Data exfiltration vector |
| Credential access | Secrets disclosure |

Approval is logged with timestamp, user, and justification.

```python
# In scripts, pre-approve a specific operation
session = ScienceSession(allow_approvals=["code_execution:script.py"])
```

For unattended pipelines, scope approvals narrowly rather than disabling the broker.

---

## Credential Management

### DO

✅ Store secrets in `.env` (git-ignored)
✅ Use `openscience credentials set` for keyring storage
✅ Rotate API keys regularly
✅ Use one key per environment (dev/prod)
✅ Set NCBI API key to raise rate limits legitimately

### DON'T

❌ Hardcode keys in source
❌ Commit `.env` to git
❌ Share keys across team members
❌ Log credentials

### Verify git hygiene

```bash
# Pre-commit hook that catches leaked keys
pre-commit run detect-private-key --all-files

# Audit history (if you suspect a leak)
git log -p | grep -i "sk-" || echo "clean"
```

If a key leaks, **revoke it immediately** and rotate.

---

## Biosecurity Safeguards

openScience includes screening for **dual-use research of concern (DURC)** — work that could be misused.

### Automatic screening

Tasks that touch flagged domains are routed through a biosecurity review layer:

- Synthesis workflows for select agents
- Gain-of-function protocol requests
- Pathogen engineering without documented oversight

### What happens on a flagged task

1. Task is paused
2. User is prompted for an institutional review reference (IBC/IRB number)
3. Approved tasks proceed under enhanced logging
4. Unapproved tasks are refused with guidance

### Your responsibilities

- Comply with your institution's IBC policies
- Report potential dual-use concerns to your biosafety officer
- Do not use openScience for activities prohibited by the [Biological Weapons Convention](https://www.un.org/disarmament/biological-weapons/)

---

## Audit Logging

Every agent call is recorded:

```json
{
  "timestamp": "2025-06-12T14:23:07Z",
  "session_id": "sess_abc123",
  "agent": "scanpy_specialist",
  "task": "QC and clustering",
  "parameters": {"min_genes": 200, "resolution": 0.5},
  "skills_called": ["scanpy.qc", "scanpy.normalize", "scanpy.leiden"],
  "artifacts": ["results/adata_clustered.h5ad"],
  "approvals": [],
  "duration_ms": 42150
}
```

Logs are retained per `logging.retention_days` (default 30) and can be exported for compliance.

---

## REST API Security

The bundled Flask server is designed for `localhost`. **Do not expose it directly to the internet.**

### For remote deployment

Put it behind an authenticating reverse proxy:

```nginx
# nginx + OIDC example
location / {
    auth_request /oauth2/auth;
    proxy_pass http://localhost:8080;
}
```

Recommended proxy layers:

- OAuth2-Proxy with your institution's IdP
- nginx + client certificates (mTLS)
- Cloudflare Access / Tailscale for lab networks

### Session isolation

Each user should have their own `ScienceSession`. The default server uses a single session for simplicity — production deployments must scope sessions per authenticated user.

---

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Email **<security@openscience.dev>** with:

1. Description
2. Steps to reproduce
3. Impact assessment
4. Suggested remediation (optional)

We follow a 90-day coordinated disclosure policy.

---

## Security Checklist for Deployments

- [ ] `SANDBOX_ENABLED=true`
- [ ] Network policy is `allowlist`, not `permissive`
- [ ] API behind authenticated proxy if remote
- [ ] Postgres/Redis not exposed to the internet
- [ ] Credentials stored in keyring, not plaintext
- [ ] `data/raw` mounted read-only
- [ ] Audit log retention configured per policy
- [ ] Regular dependency updates (`pip-audit`)
- [ ] Human approval broker active for sensitive ops

---

## Dependency Security

Check for known CVEs:

```bash
pip install pip-audit
pip-audit
```

GitHub Dependabot is enabled on the repository and opens PRs for vulnerable dependencies.

---

## See Also

- [Configuration](configuration.md) — sandbox and credential settings
- [Architecture](architecture.md) — how layers fit together
- [Docker](docker.md) — production hardening
