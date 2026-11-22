# EXPERIMENT 10: Comprehensive Library Build Tests

**Date:** 2026-11-22  
**Project:** openScience v0.1.0  
**Experiment:** Library Build, Install, and CLI Verification  

## Test Environment

- **OS:** macOS (Darwin)
- **Python:** $(python3 --version 2>/dev/null || echo "Not found")
- **pip:** $(pip3 --version 2>/dev/null || echo "Not found")
- **Working Directory:** `/Users/srubaiat/openScience`

## Test Summary

| Test # | Test Description | Status | Notes |
|--------|------------------|--------|-------|
| 1 | pip install -e . (development mode) | ⏳ Pending | |
| 2 | python setup.py build | ⏳ Pending | |
| 3 | python setup.py sdist (source distribution) | ⏳ Pending | |
| 4 | python setup.py bdist_wheel (wheel distribution) | ⏳ Pending | |
| 5 | pip install dist/openscience-0.1.0-py3-none-any.whl | ⏳ Pending | |
| 6 | Test import openscience (after install) | ⏳ Pending | |
| 7 | CLI: openscience --help | ⏳ Pending | |
| 8 | CLI: openscience init | ⏳ Pending | |
| 9 | CLI: openscience agents | ⏳ Pending | |
| 10 | Library in fresh virtual environment | ⏳ Pending | |

## Detailed Test Results

### Test 1: pip install -e . (Development Mode)

**Command:**
```bash
cd /Users/srubaiat/openScience && pip install -e . -v
```

**Status:** ⏳ Pending

**Output:**
```
(To be executed)
```

**Verification Steps:**
1. Verify package installed in development mode: `pip list | grep openscience`
2. Verify egg-info created: `ls -la src/openscience.egg-info/`
3. Verify package structure intact

---

### Test 2: python setup.py build

**Command:**
```bash
cd /Users/srubaiat/openScience && python setup.py build
```

**Status:** ⏳ Pending

**Output:**
```
(To be executed)
```

**Verification Steps:**
1. Check `build/` directory created
2. Verify `build/lib/openscience/` exists
3. Check all submodules present

---

### Test 3: python setup.py sdist (Source Distribution)

**Command:**
```bash
cd /Users/srubaiat/openScience && python setup.py sdist
```

**Status:** ⏳ Pending

**Output:**
```
(To be executed)
```

**Verification Steps:**
1. Check `dist/` directory created
2. Verify `dist/openscience-0.1.0.tar.gz` exists
3. Validate tarball contents

---

### Test 4: python setup.py bdist_wheel (Wheel Distribution)

**Command:**
```bash
cd /Users/srubaiat/openScience && python setup.py bdist_wheel
```

**Status:** ⏳ Pending

**Output:**
```
(To be executed)
```

**Verification Steps:**
1. Check `dist/openscience-0.1.0-py3-none-any.whl` exists
2. Validate wheel structure: `unzip -l dist/openscience-0.1.0-py3-none-any.whl`

---

### Test 5: pip install dist/openscience-0.1.0-py3-none-any.whl

**Command:**
```bash
pip install dist/openscience-0.1.0-py3-none-any.whl --force-reinstall
```

**Status:** ⏳ Pending

**Output:**
```
(To be executed)
```

**Verification Steps:**
1. Verify installation: `pip show openscience`
2. Check library location: `python -c "import openscience; print(openscience.__file__)"`

---

### Test 6: Test import openscience (After Install)

**Command:**
```bash
python -c "import openscience; print(f'Version: {openscience.__version__}'); print(f'Path: {openscience.__file__}')"
```

**Status:** ⏳ Pending

**Output:**
```
(To be executed)
```

**Verification Steps:**
1. Import succeeds without errors
2. Version is "0.1.0"
3. Path points to installed location

---

### Test 7: CLI: openscience --help

**Command:**
```bash
openscience --help
```

**Status:** ⏳ Pending

**Output:**
```
(To be executed)
```

**Verification Steps:**
1. CLI command executes
2. Help text displays
3. All commands listed

---

### Test 8: CLI: openscience init

**Command:**
```bash
cd /tmp && openscience init --project-dir test_openscience_project
```

**Status:** ⏳ Pending

**Output:**
```
(To be executed)
```

**Verification Steps:**
1. Project directory created
2. Subdirectories: data/raw, data/processed, results, figures, notebooks, config
3. openscience.yaml config file created

---

### Test 9: CLI: openscience agents

**Command:**
```bash
openscience agents
```

**Status:** ⏳ Pending

**Output:**
```
(To be executed)
```

**Verification Steps:**
1. Command executes without error
2. Agent list displays
3. Count shows 111 agents (or documented number)

---

### Test 10: Library in Fresh Virtual Environment

**Commands:**
```bash
# Create fresh venv
python -m venv /tmp/openscience_test_venv
source /tmp/openscience_test_venv/bin/activate

# Install from wheel
pip install dist/openscience-0.1.0-py3-none-any.whl

# Test import
python -c "import openscience; print(openscience.__version__)"

# Test CLI
openscience --version
```

**Status:** ⏳ Pending

**Output:**
```
(To be executed)
```

**Verification Steps:**
1. Fresh venv created successfully
2. Wheel installs without dependency errors
3. Import works in isolated environment
4. CLI works in isolated environment

---

## Package Structure Verification

**Expected Structure:**
```
openscience/
├── __init__.py          # Version: 0.1.0
├── cli.py               # CLI entry point
├── server.py            # Web server
├── agents/              # Agent modules (111+ agents)
├── api/                 # REST API
├── core/                # Core framework
│   ├── agent.py
│   ├── orchestrator.py
│   ├── sandbox.py
│   └── session.py
├── connectors/          # Data connectors
├── compute/             # Compute backends
├── security/            # Security modules
├── skills/              # Analysis skills
└── workers/             # Background workers
```

---

## Issues Found and Resolutions

| Issue | Severity | Resolution | Status |
|-------|----------|------------|--------|
| (To be documented) | | | |

---

## Post-Test Validation

- [ ] All 10 tests pass
- [ ] No import errors
- [ ] CLI commands functional
- [ ] Wheel distribution valid
- [ ] Fresh venv installation successful
- [ ] Package structure complete

---

## Recommendations

(To be added after testing)

---

## Appendix: Environment Details

```bash
# Python environment
Python: $(python3 --version 2>/dev/null)
pip: $(pip3 --version 2>/dev/null)
setuptools: $(pip3 show setuptools 2>/dev/null | grep Version)
wheel: $(pip3 show wheel 2>/dev/null | grep Version)

# Project structure
Project tree: $(tree -L 3 -I '__pycache__|*.egg-info|.git' . 2>/dev/null || find . -maxdepth 3 -type d | head -30)
```
