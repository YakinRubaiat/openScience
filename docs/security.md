# Security

openScience is designed around a deny-by-default posture: agent capabilities
start at zero and are granted explicitly through a human-approval broker.

## Principles

### OS-Level Sandbox

- **Deny-by-default network egress** — agents cannot reach the network unless
  a connector's destination is explicitly allowed.
- **File-system guards** — writes are confined to the session workspace;
  anything outside requires approval.
- **Process isolation** — skills run in per-specialist Conda environments to
  contain dependency conflicts and supply-chain surprises.

### Human-Approval Broker

Privileged actions queue for human approval before executing:

- Arbitrary code execution
- Outbound network requests to new destinations
- File deletions and writes outside the workspace

Tasks wait in `awaiting_approval` until a human approves or denies via the UI
or the [API](api.md).

### Biosecurity Safeguards

- **Dual-use review** — workflows flagged as potential dual-use research of
  concern are routed through additional human review.
- **Audit trail** — every approved and denied action is logged with the full
  agent chain that requested it.

### Credential Handling

- Connector credentials (PubMed, AWS, …) live in the **OS keyring**, never in
  `.env`, source, or container images.
- `.env` holds only deployment secrets (`DB_PASSWORD`, `SECRET_KEY`, …) and
  must never be committed. `.gitignore` excludes it; the committed
  `.env.example` contains only placeholders.

## Reporting a Vulnerability

**Do not open a public GitHub issue.** Email the maintainers (see
`CONTRIBUTING.md` for contact) with:

- A description of the issue and affected versions
- Reproduction steps or proof of concept
- Suggested severity

You will receive acknowledgment within 72 hours. Fixes are coordinated before
public disclosure.

## Security Testing

The `security.yml` GitHub Actions workflow runs on every PR:

- **bandit** — static security analysis of the Python source
- **pip-audit** — known-vulnerability scan of dependencies
- Docker image scanning on release builds

Run the same checks locally:

```bash
pip install -e ".[dev]"
bandit -c pyproject.toml -r src
pip-audit
```

## Deployment Hardening Checklist

- [ ] All default passwords in `.env` replaced
- [ ] `SECRET_KEY` generated with `openssl rand -hex 32`
- [ ] PostgreSQL (5432) and Redis (6379) not exposed to the public internet
- [ ] TLS enabled via `docker-compose.prod.yml` with real `DOMAIN`/`SSL_EMAIL`
- [ ] `LOG_LEVEL` at `WARNING` or higher in production
- [ ] Regular `pip-audit` runs against the deployed lockfile
- [ ] Database backups encrypted at rest

## Related

- [Configuration](configuration.md) — secrets and keyring setup
- [Docker Guide](docker.md) — production checklist
- [Contributing](contributing.md) — disclosure contact
