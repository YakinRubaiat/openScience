#!/bin/bash
# Validate complete Docker infrastructure

set -e

echo "🔍 Docker Infrastructure Validation"
echo "===================================="
echo ""

PASSED=0
FAILED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

validate() {
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $1"
        ((FAILED++))
    fi
    return $exit_code
}

# Check Docker installation
echo "Checking Docker installation..."
docker --version > /dev/null 2>&1
validate "Docker is installed"

docker-compose --version > /dev/null 2>&1 || docker compose version > /dev/null 2>&1
validate "Docker Compose is installed"

echo ""
echo "Validating configuration files..."

# Validate docker-compose.yml
docker-compose config --quiet > /dev/null 2>&1
validate "docker-compose.yml is valid"

# Validate docker-compose.test.yml
docker-compose -f docker-compose.test.yml config --quiet > /dev/null 2>&1
validate "docker-compose.test.yml is valid"

# Validate docker-compose.prod.yml (with env vars)
if [ -f .env ]; then
    docker-compose -f docker-compose.prod.yml config --quiet > /dev/null 2>&1
    validate "docker-compose.prod.yml is valid"
else
    echo -e "${YELLOW}⊘${NC} docker-compose.prod.yml (skipped - no .env file)"
fi

echo ""
echo "Checking required files..."

# Check Dockerfiles
[ -f Dockerfile.api ] && validate "Dockerfile.api exists"
[ -f Dockerfile.ui ] && validate "Dockerfile.ui exists"
[ -f Dockerfile.worker ] && validate "Dockerfile.worker exists"
[ -f Dockerfile.test ] && validate "Dockerfile.test exists"
[ -f .dockerignore ] && validate ".dockerignore exists"
[ -f .env.example ] && validate ".env.example exists"

echo ""
echo "Checking documentation..."

[ -f docker/README.md ] && validate "docker/README.md exists"
[ -f DOCKER_SUMMARY.md ] && validate "DOCKER_SUMMARY.md exists"

echo ""
echo "Checking utility scripts..."

[ -f docker/quick-start.sh ] && [ -x docker/quick-start.sh ] && validate "quick-start.sh is executable"
[ -f docker/docker-utils.sh ] && [ -x docker/docker-utils.sh ] && validate "docker-utils.sh is executable"
[ -f docker/cleanup.sh ] && [ -x docker/cleanup.sh ] && validate "cleanup.sh is executable"

echo ""
echo "Checking configuration files..."

[ -f docker/init-db.sql ] && validate "init-db.sql exists"
[ -f docker/nginx-ui.conf ] && validate "nginx-ui.conf exists"
[ -f docker/nginx-prod.conf ] && validate "nginx-prod.conf exists"
[ -f docker/prometheus.yml ] && validate "prometheus.yml exists"

echo ""
echo "Checking source code structure..."

[ -f src/openscience/server.py ] && validate "server.py exists"
[ -f src/openscience/api/__init__.py ] && validate "api/__init__.py exists"
[ -f src/openscience/workers/__init__.py ] && validate "workers/__init__.py exists"
[ -f src/openscience/workers/tasks.py ] && validate "workers/tasks.py exists"

echo ""
echo "Checking test files..."

[ -f tests/test_server.py ] && validate "test_server.py exists"
[ -f tests/test_workers.py ] && validate "test_workers.py exists"
[ -f pytest.ini ] && validate "pytest.ini exists"

echo ""
echo "Checking UI files..."

[ -f ui/package.json ] && validate "ui/package.json exists"
[ -f ui/vite.config.js ] && validate "ui/vite.config.js exists"
[ -f ui/index.html ] && validate "ui/index.html exists"
[ -f ui/src/main.jsx ] && validate "ui/src/main.jsx exists"
[ -f ui/src/App.jsx ] && validate "ui/src/App.jsx exists"

echo ""
echo "===================================="
echo -e "Results: ${GREEN}${PASSED} passed${NC}, ${RED}${FAILED} failed${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All validations passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Copy .env.example to .env and configure"
    echo "  2. Run ./docker/quick-start.sh"
    echo "  3. Read docker/README.md for more details"
    exit 0
else
    echo -e "${RED}❌ Some validations failed${NC}"
    exit 1
fi
