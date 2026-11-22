#!/bin/bash
# Script to manage Docker environments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if .env exists
check_env() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        print_warning ".env file not found"
        print_info "Copying .env.example to .env"
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        print_warning "Please update .env with your configuration"
    fi
}

# Development commands
dev_up() {
    print_info "Starting development environment..."
    check_env
    cd "$PROJECT_ROOT"
    docker-compose up -d
    print_success "Development environment started"
    print_info "API: http://localhost:5000"
    print_info "UI: http://localhost:3000"
    print_info "Flower: http://localhost:5555"
}

dev_down() {
    print_info "Stopping development environment..."
    cd "$PROJECT_ROOT"
    docker-compose down
    print_success "Development environment stopped"
}

dev_logs() {
    cd "$PROJECT_ROOT"
    docker-compose logs -f "$@"
}

dev_rebuild() {
    print_info "Rebuilding development environment..."
    cd "$PROJECT_ROOT"
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    print_success "Development environment rebuilt"
}

# Test commands
test_run() {
    print_info "Running tests..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.test.yml run --rm test
    print_success "Tests completed"
}

test_lint() {
    print_info "Running linters..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.test.yml run --rm lint
    print_success "Linting completed"
}

# Production commands
prod_up() {
    print_info "Starting production environment..."
    check_env
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.prod.yml up -d
    print_success "Production environment started"
}

prod_down() {
    print_info "Stopping production environment..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.prod.yml down
    print_success "Production environment stopped"
}

prod_logs() {
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.prod.yml logs -f "$@"
}

# Utility commands
status() {
    print_info "Service status:"
    cd "$PROJECT_ROOT"
    docker-compose ps
}

clean() {
    print_warning "This will remove all containers, volumes, and images"
    read -p "Are you sure? (yes/no) " -r
    if [[ $REPLY =~ ^yes$ ]]; then
        print_info "Cleaning up Docker resources..."
        cd "$PROJECT_ROOT"
        docker-compose down -v
        docker-compose -f docker-compose.prod.yml down -v
        docker-compose -f docker-compose.test.yml down -v
        print_success "Cleanup completed"
    fi
}

backup_db() {
    BACKUP_FILE="$PROJECT_ROOT/backups/backup_$(date +%Y%m%d_%H%M%S).sql"
    mkdir -p "$PROJECT_ROOT/backups"
    print_info "Creating database backup: $BACKUP_FILE"
    cd "$PROJECT_ROOT"
    docker-compose exec -T db pg_dump -U openscience openscience > "$BACKUP_FILE"
    print_success "Backup created: $BACKUP_FILE"
}

restore_db() {
    if [ -z "$1" ]; then
        print_error "Please provide backup file"
        echo "Usage: $0 restore-db <backup_file>"
        exit 1
    fi
    print_warning "This will restore the database from: $1"
    read -p "Are you sure? (yes/no) " -r
    if [[ $REPLY =~ ^yes$ ]]; then
        print_info "Restoring database..."
        cd "$PROJECT_ROOT"
        docker-compose exec -T db psql -U openscience openscience < "$1"
        print_success "Database restored"
    fi
}

# Help
show_help() {
    cat << EOF
openScience Docker Management Script

Usage: $0 <command> [options]

Development Commands:
    dev-up          Start development environment
    dev-down        Stop development environment
    dev-logs        View development logs (optional: service name)
    dev-rebuild     Rebuild and restart development environment

Test Commands:
    test            Run tests
    test-lint       Run code linters

Production Commands:
    prod-up         Start production environment
    prod-down       Stop production environment
    prod-logs       View production logs (optional: service name)

Utility Commands:
    status          Show service status
    clean           Remove all containers, volumes, and images
    backup-db       Create database backup
    restore-db      Restore database from backup
    help            Show this help message

Examples:
    $0 dev-up               # Start development environment
    $0 dev-logs api         # View API logs
    $0 test                 # Run tests
    $0 prod-up              # Start production environment
    $0 backup-db            # Backup database

EOF
}

# Main
case "$1" in
    dev-up)
        dev_up
        ;;
    dev-down)
        dev_down
        ;;
    dev-logs)
        shift
        dev_logs "$@"
        ;;
    dev-rebuild)
        dev_rebuild
        ;;
    test)
        test_run
        ;;
    test-lint)
        test_lint
        ;;
    prod-up)
        prod_up
        ;;
    prod-down)
        prod_down
        ;;
    prod-logs)
        shift
        prod_logs "$@"
        ;;
    status)
        status
        ;;
    clean)
        clean
        ;;
    backup-db)
        backup_db
        ;;
    restore-db)
        shift
        restore_db "$@"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
