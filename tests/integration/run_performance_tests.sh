#!/bin/bash
# Performance Test Suite Runner for openScience
# Runs all 10 comprehensive performance tests

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "═══════════════════════════════════════════════════════════════════════"
echo "  openScience Performance Test Suite"
echo "  Running 10 comprehensive tests..."
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "❌ Error: Virtual environment not found at $PROJECT_ROOT/.venv"
    echo "   Run: python -m venv .venv && source .venv/bin/activate && pip install -e .[test]"
    exit 1
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source "$PROJECT_ROOT/.venv/bin/activate"

# Check if performance tools are installed
echo "✅ Checking performance tools..."
pip list | grep -q "pytest-benchmark" || {
    echo "   Installing performance testing dependencies..."
    pip install pytest-benchmark memory-profiler py-spy locust psutil requests
}

# Start API server
echo ""
echo "✅ Starting openScience API server..."
cd "$PROJECT_ROOT"
python -m openscience.server > /tmp/openscience_perf_test.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "   Waiting for server to be ready..."
for i in {1..10}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "   ✅ Server is healthy"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   ❌ Server failed to start"
        cat /tmp/openscience_perf_test.log
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Run performance tests
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "  Running Performance Tests..."
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

pytest tests/integration/test_performance.py -v -s --tb=short

TEST_EXIT_CODE=$?

# Stop server
echo ""
echo "✅ Stopping API server..."
kill $SERVER_PID 2>/dev/null || true
sleep 1

# Show results
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "  ✅ All Performance Tests PASSED"
else
    echo "  ⚠️  Some tests failed (exit code: $TEST_EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "📊 Results:"
ls -lh tests/integration/performance_results/*.json | tail -10
echo ""
echo "📁 Full report: tests/integration/EXPERIMENT_07_PERFORMANCE.md"
echo "📋 Summary:     tests/integration/PERFORMANCE_SUMMARY.txt"
echo ""

exit $TEST_EXIT_CODE
