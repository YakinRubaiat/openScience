# Contributing

Thank you for your interest in contributing to openScience! The canonical
guidelines live in the repository root ([CONTRIBUTING.md](https://github.com/YakinRubaiat/openScience/blob/main/CONTRIBUTING.md));
this page summarizes the workflow.

## Code of Conduct

Be kind, be constructive, and assume good faith. Harassment of any kind is
not tolerated.

## Ways to Contribute

- **Bug reports** — open an issue with reproduction steps and your
  environment (OS, Python/Docker versions).
- **Feature requests** — open an issue describing the scientific workflow
  you want to enable.
- **Agents and skills** — new specialist agents, skills, or connectors.
- **Documentation** — fixes and expansions to these docs.
- **Code** — bug fixes and features via pull request.

## Development Workflow

1. Fork and clone the repository.
2. Set up your environment per the [Development](development.md) guide:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev,test]"
   ```

3. Create a branch:

   ```bash
   git checkout -b feature/short-description
   ```

4. Make your change. Follow the existing style — black formatting,
   line length 100, and type annotations (mypy runs in strict mode).
5. Add or update tests in `tests/`.
6. Run the checks:

   ```bash
   black src tests
   ruff check src tests
   mypy src
   pytest
   ```

7. Commit with a clear message and open a pull request against `main`.

## Pull Request Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Linters clean (`black`, `ruff`, `mypy`)
- [ ] New behavior covered by tests
- [ ] Documentation updated (docstrings, and `docs/` for user-facing changes)
- [ ] `CHANGELOG.md` entry for notable changes
- [ ] No secrets or credentials committed

## Adding a New Agent

1. Define the agent in `src/openscience/agents/` with typed inputs, outputs,
   and declared skills.
2. Document it in the [Agent Catalog](agents.md) in the matching category.
3. Add tests under `tests/core/`.
4. If it needs new dependencies, gate them behind an existing extra in
   `pyproject.toml` (`bio`, `chem`, `ml`, `viz`) or propose a new one.

## Security Issues

Do **not** open a public issue for vulnerabilities — see the responsible
disclosure process in [Security](security.md).

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](https://github.com/YakinRubaiat/openScience/blob/main/LICENSE).
