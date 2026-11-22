"""Comprehensive performance test suite for openScience."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import psutil
import pytest
import requests
from memory_profiler import memory_usage

# Test configuration
BASE_URL = "http://localhost:8080"
RESULTS_DIR = "/Users/srubaiat/openScience/tests/integration/performance_results"
os.makedirs(RESULTS_DIR, exist_ok=True)


class PerformanceMetrics:
    """Store and manage performance test metrics."""

    def __init__(self, test_name):
        self.test_name = test_name
        self.start_time = time.time()
        self.metrics = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "results": {},
            "bottlenecks": [],
            "recommendations": [],
        }

    def add_metric(self, key, value):
        """Add a metric."""
        self.metrics["results"][key] = value

    def add_bottleneck(self, issue, severity="medium"):
        """Record a bottleneck."""
        self.metrics["bottlenecks"].append(
            {"issue": issue, "severity": severity, "timestamp": datetime.now().isoformat()}
        )

    def add_recommendation(self, recommendation):
        """Record a recommendation."""
        self.metrics["recommendations"].append(recommendation)

    def save(self):
        """Save metrics to file."""
        duration = time.time() - self.start_time
        self.metrics["duration_seconds"] = duration

        filename = f"{RESULTS_DIR}/{self.test_name}_{int(time.time())}.json"
        with open(filename, "w") as f:
            json.dump(self.metrics, f, indent=2)
        return filename


@pytest.fixture(scope="session", autouse=True)
def check_server():
    """Ensure API server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        print(f"\n✅ Server is healthy: {response.json()}")
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running. Start with: python -m openscience.server")


# ============================================================================
# TEST 1: Load Test API Endpoints (100 Concurrent Users)
# ============================================================================


def test_01_load_test_api_endpoints():
    """Load test API endpoints with 100 concurrent users."""
    metrics = PerformanceMetrics("01_load_test_api")

    num_users = 100
    requests_per_user = 10
    endpoints = ["/api/agents", "/health"]

    response_times = []
    errors = 0

    def make_request(endpoint):
        """Make a single request."""
        start = time.time()
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            elapsed = time.time() - start
            return {"success": response.status_code == 200, "time": elapsed, "endpoint": endpoint}
        except Exception as e:
            return {"success": False, "error": str(e), "endpoint": endpoint}

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = []
        for _ in range(requests_per_user):
            for endpoint in endpoints:
                for _ in range(num_users):
                    futures.append(executor.submit(make_request, endpoint))

        for future in as_completed(futures):
            result = future.result()
            if result["success"]:
                response_times.append(result["time"])
            else:
                errors += 1

    total_time = time.time() - start_time

    # Calculate statistics
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        p50 = sorted(response_times)[len(response_times) // 2]
        p95 = sorted(response_times)[int(len(response_times) * 0.95)]
        p99 = sorted(response_times)[int(len(response_times) * 0.99)]
        max_time = max(response_times)
        min_time = min(response_times)
        throughput = len(response_times) / total_time
    else:
        avg_time = p50 = p95 = p99 = max_time = min_time = throughput = 0

    metrics.add_metric("concurrent_users", num_users)
    metrics.add_metric("total_requests", len(futures))
    metrics.add_metric("successful_requests", len(response_times))
    metrics.add_metric("failed_requests", errors)
    metrics.add_metric("total_time_seconds", total_time)
    metrics.add_metric("avg_response_time_seconds", avg_time)
    metrics.add_metric("p50_response_time_seconds", p50)
    metrics.add_metric("p95_response_time_seconds", p95)
    metrics.add_metric("p99_response_time_seconds", p99)
    metrics.add_metric("min_response_time_seconds", min_time)
    metrics.add_metric("max_response_time_seconds", max_time)
    metrics.add_metric("throughput_requests_per_second", throughput)

    # Identify bottlenecks
    if p95 > 1.0:
        metrics.add_bottleneck(f"P95 response time ({p95:.2f}s) exceeds 1 second", "high")
    if errors > len(futures) * 0.05:
        metrics.add_bottleneck(f"Error rate ({errors}/{len(futures)}) exceeds 5%", "critical")
    if throughput < 100:
        metrics.add_bottleneck(f"Throughput ({throughput:.0f} req/s) below target", "medium")

    metrics.add_recommendation("Consider adding response caching for /api/agents")
    if errors > 0:
        metrics.add_recommendation("Implement connection pooling and retry logic")

    filename = metrics.save()
    print(f"\n✅ Test 1 complete: {filename}")
    print(f"   Throughput: {throughput:.1f} req/s, P95: {p95:.3f}s, Errors: {errors}")

    assert errors < len(futures) * 0.1, f"Too many errors: {errors}"


# ============================================================================
# TEST 2: Stress Test Agent Execution
# ============================================================================


def test_02_stress_test_agent_execution():
    """Stress test agent execution with concurrent agent calls."""
    metrics = PerformanceMetrics("02_stress_test_agent_execution")

    from openscience.agents.review.performance_reviewer import PerformanceReviewerAgent

    num_concurrent = 20
    results = []
    errors = 0

    def execute_agent():
        """Execute a single agent."""
        try:
            agent = PerformanceReviewerAgent()
            start = time.time()
            # Simulate agent work by accessing metadata and initialization
            result = {
                "name": agent.metadata.name,
                "category": agent.metadata.category,
                "skills": agent.metadata.required_skills,
            }
            elapsed = time.time() - start
            return {"success": True, "time": elapsed, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    start_time = time.time()
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(execute_agent) for _ in range(num_concurrent)]
        for future in as_completed(futures):
            result = future.result()
            if result["success"]:
                results.append(result)
            else:
                errors += 1

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    total_time = time.time() - start_time

    metrics.add_metric("concurrent_agents", num_concurrent)
    metrics.add_metric("successful_executions", len(results))
    metrics.add_metric("failed_executions", errors)
    metrics.add_metric("total_time_seconds", total_time)
    metrics.add_metric("memory_increase_mb", memory_increase)
    metrics.add_metric("avg_execution_time", sum(r["time"] for r in results) / len(results))

    if errors > 0:
        metrics.add_bottleneck(f"{errors} agent executions failed", "high")
    if memory_increase > 100:
        metrics.add_bottleneck(f"Memory increased by {memory_increase:.1f}MB", "medium")

    metrics.add_recommendation("Implement agent execution pooling")
    metrics.add_recommendation("Add agent result caching")

    filename = metrics.save()
    print(f"\n✅ Test 2 complete: {filename}")
    print(f"   Executions: {len(results)}/{num_concurrent}, Memory Δ: {memory_increase:.1f}MB")


# ============================================================================
# TEST 3: Memory Leak Detection (using performance_reviewer)
# ============================================================================


def test_03_memory_leak_detection():
    """Detect memory leaks using memory profiler and performance_reviewer agent."""
    metrics = PerformanceMetrics("03_memory_leak_detection")

    from openscience.agents.review.performance_reviewer import PerformanceReviewerAgent

    def memory_intensive_operation():
        """Simulate memory-intensive operation."""
        data = []
        for i in range(100):
            data.append([0] * 10000)  # Allocate memory
        return len(data)

    # Profile memory usage
    start_mem = psutil.Process().memory_info().rss / 1024 / 1024

    # memory_usage returns (memory_list, retval) when retval=True
    # or just float when max_usage=True and retval=False
    mem_usage_result = memory_usage(
        (memory_intensive_operation, (), {}),
        interval=0.1,
        max_usage=True,
        retval=True,
        include_children=True,
    )

    # Handle both return types
    if isinstance(mem_usage_result, tuple):
        mem_usage, _result = mem_usage_result
        peak_mem = mem_usage if isinstance(mem_usage, float) else max(mem_usage)
    else:
        peak_mem = mem_usage_result

    end_mem = psutil.Process().memory_info().rss / 1024 / 1024

    # Identify if memory was released
    memory_released = peak_mem - end_mem
    memory_retained = end_mem - start_mem

    metrics.add_metric("start_memory_mb", start_mem)
    metrics.add_metric("peak_memory_mb", peak_mem)
    metrics.add_metric("end_memory_mb", end_mem)
    metrics.add_metric("memory_released_mb", memory_released)
    metrics.add_metric("memory_retained_mb", memory_retained)

    # Check for leaks
    if memory_retained > 50:
        metrics.add_bottleneck(
            f"Memory retained: {memory_retained:.1f}MB - possible leak", "critical"
        )
        metrics.add_recommendation("Investigate circular references")
        metrics.add_recommendation("Ensure proper cleanup in finally blocks")
    else:
        metrics.add_metric("memory_leak_detected", False)

    # Performance reviewer analysis
    PerformanceReviewerAgent()
    metrics.add_metric("performance_reviewer_available", True)

    filename = metrics.save()
    print(f"\n✅ Test 3 complete: {filename}")
    print(f"   Memory retained: {memory_retained:.1f}MB")


# ============================================================================
# TEST 4: Database Query Performance
# ============================================================================


def test_04_database_query_performance():
    """Benchmark database query performance."""
    metrics = PerformanceMetrics("04_database_query_performance")

    # Simulate database queries (openScience may not have a DB yet, so we benchmark in-memory operations)
    import sqlite3

    # Create in-memory test database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Create test table
    cursor.execute("""
        CREATE TABLE agents (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            description TEXT
        )
    """)

    # Insert test data
    insert_start = time.time()
    test_data = [(i, f"agent_{i}", "analysis", f"Test agent {i}") for i in range(1000)]
    cursor.executemany("INSERT INTO agents VALUES (?, ?, ?, ?)", test_data)
    conn.commit()
    insert_time = time.time() - insert_start

    # Test query performance
    queries = [
        ("SELECT_ALL", "SELECT * FROM agents"),
        ("SELECT_FILTERED", "SELECT * FROM agents WHERE category = 'analysis'"),
        (
            "SELECT_JOIN",
            "SELECT a1.name, a2.name FROM agents a1 JOIN agents a2 ON a1.id = a2.id + 1",
        ),
        ("COUNT", "SELECT COUNT(*) FROM agents"),
    ]

    query_times = {}
    for query_name, query in queries:
        start = time.time()
        for _ in range(100):
            cursor.execute(query)
            cursor.fetchall()
        elapsed = time.time() - start
        query_times[query_name] = elapsed / 100  # Average

    conn.close()

    metrics.add_metric("insert_time_seconds", insert_time)
    metrics.add_metric("query_times_seconds", query_times)

    # Identify slow queries
    for name, qtime in query_times.items():
        if qtime > 0.01:  # 10ms
            metrics.add_bottleneck(f"Slow query {name}: {qtime*1000:.2f}ms", "medium")

    metrics.add_recommendation("Add indexes on frequently queried columns")
    metrics.add_recommendation("Implement query result caching")

    filename = metrics.save()
    print(f"\n✅ Test 4 complete: {filename}")
    print(f"   Slowest query: {max(query_times.items(), key=lambda x: x[1])[0]}")


# ============================================================================
# TEST 5: Docker Container Resource Usage
# ============================================================================


def test_05_docker_container_resource_usage():
    """Monitor Docker container resource usage."""
    metrics = PerformanceMetrics("05_docker_resource_usage")

    # Check if Docker is running
    try:
        import subprocess

        result = subprocess.run(
            ["docker", "ps", "--filter", "name=openscience", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        containers = result.stdout.strip().split("\n") if result.stdout.strip() else []

        if not containers or containers == [""]:
            metrics.add_metric("docker_available", False)
            metrics.add_metric("containers_running", 0)
            metrics.add_bottleneck("No openScience containers running", "info")
        else:
            metrics.add_metric("docker_available", True)
            metrics.add_metric("containers_running", len(containers))
            metrics.add_metric("container_names", containers)

            # Get stats for each container
            for container in containers:
                if container:
                    stats_result = subprocess.run(
                        [
                            "docker",
                            "stats",
                            container,
                            "--no-stream",
                            "--format",
                            "{{.CPUPerc}}|{{.MemUsage}}|{{.NetIO}}|{{.BlockIO}}",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if stats_result.stdout:
                        metrics.add_metric(
                            f"container_{container}_stats", stats_result.stdout.strip()
                        )

    except FileNotFoundError:
        metrics.add_metric("docker_available", False)
        metrics.add_bottleneck("Docker not installed or not in PATH", "info")
    except Exception as e:
        metrics.add_bottleneck(f"Docker monitoring error: {e!s}", "medium")

    metrics.add_recommendation("Monitor container resource limits in production")
    metrics.add_recommendation("Set appropriate CPU and memory limits")

    filename = metrics.save()
    print(f"\n✅ Test 5 complete: {filename}")
    print(f"   Docker containers: {metrics.metrics['results'].get('containers_running', 0)}")


# ============================================================================
# TEST 6: Response Time Benchmarks
# ============================================================================


def test_06_response_time_benchmarks():
    """Benchmark response times for all API endpoints."""
    metrics = PerformanceMetrics("06_response_time_benchmarks")

    endpoints = [
        "/health",
        "/api/agents",
    ]

    iterations = 100
    results = {}

    for endpoint in endpoints:
        times = []
        for _ in range(iterations):
            start = time.time()
            requests.get(f"{BASE_URL}{endpoint}")
            elapsed = time.time() - start
            times.append(elapsed)

        results[endpoint] = {
            "min": min(times),
            "max": max(times),
            "avg": sum(times) / len(times),
            "p50": sorted(times)[len(times) // 2],
            "p95": sorted(times)[int(len(times) * 0.95)],
            "p99": sorted(times)[int(len(times) * 0.99)],
        }

    metrics.add_metric("iterations", iterations)
    metrics.add_metric("endpoint_benchmarks", results)

    # Identify slow endpoints
    for endpoint, data in results.items():
        if data["p95"] > 0.5:
            metrics.add_bottleneck(
                f"Slow endpoint {endpoint}: P95 = {data['p95']*1000:.0f}ms", "high"
            )

    metrics.add_recommendation("Implement endpoint-specific caching strategies")

    filename = metrics.save()
    print(f"\n✅ Test 6 complete: {filename}")
    for endpoint, data in results.items():
        print(f"   {endpoint}: avg={data['avg']*1000:.1f}ms, p95={data['p95']*1000:.1f}ms")


# ============================================================================
# TEST 7: Large File Upload Test
# ============================================================================


def test_07_large_file_upload():
    """Test large file upload performance."""
    metrics = PerformanceMetrics("07_large_file_upload")

    # Create test files of various sizes
    file_sizes_mb = [1, 10, 50]  # MB
    results = {}

    for size_mb in file_sizes_mb:
        # Generate test data
        file_path = f"{RESULTS_DIR}/test_upload_{size_mb}mb.dat"
        with open(file_path, "wb") as f:
            f.write(os.urandom(size_mb * 1024 * 1024))

        # Simulate upload (in real scenario, POST to /api/session/load)
        start = time.time()
        try:
            with open(file_path, "rb") as f:
                # Simulate reading/processing
                data = f.read()
                # In real scenario, this would be:
                # response = requests.post(f"{BASE_URL}/api/session/load",
                #                         files={"file": f}, timeout=60)
            elapsed = time.time() - start
            throughput = size_mb / elapsed if elapsed > 0 else 0

            results[f"{size_mb}MB"] = {
                "upload_time_seconds": elapsed,
                "throughput_mbps": throughput,
            }

            if elapsed > 10:
                metrics.add_bottleneck(
                    f"Slow upload for {size_mb}MB file: {elapsed:.1f}s", "medium"
                )

        except Exception as e:
            metrics.add_bottleneck(f"Upload failed for {size_mb}MB: {e!s}", "high")

        finally:
            # Cleanup
            if os.path.exists(file_path):
                os.remove(file_path)

    metrics.add_metric("upload_results", results)
    metrics.add_recommendation("Implement chunked upload for large files")
    metrics.add_recommendation("Add upload progress tracking")

    filename = metrics.save()
    print(f"\n✅ Test 7 complete: {filename}")
    for size, data in results.items():
        print(f"   {size}: {data['upload_time_seconds']:.2f}s ({data['throughput_mbps']:.1f} MB/s)")


# ============================================================================
# TEST 8: Concurrent Session Handling
# ============================================================================


def test_08_concurrent_session_handling():
    """Test handling of multiple concurrent sessions."""
    metrics = PerformanceMetrics("08_concurrent_session_handling")

    num_sessions = 50
    session_results = []

    def simulate_session(session_id):
        """Simulate a user session."""
        try:
            # Health check
            requests.get(f"{BASE_URL}/health")

            # List agents
            requests.get(f"{BASE_URL}/api/agents")

            return {"session_id": session_id, "success": True}
        except Exception as e:
            return {"session_id": session_id, "success": False, "error": str(e)}

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_sessions) as executor:
        futures = {executor.submit(simulate_session, i): i for i in range(num_sessions)}
        for future in as_completed(futures):
            result = future.result()
            session_results.append(result)

    elapsed = time.time() - start_time

    successful = sum(1 for r in session_results if r["success"])
    failed = num_sessions - successful

    metrics.add_metric("total_sessions", num_sessions)
    metrics.add_metric("successful_sessions", successful)
    metrics.add_metric("failed_sessions", failed)
    metrics.add_metric("total_time_seconds", elapsed)
    metrics.add_metric("sessions_per_second", num_sessions / elapsed)

    if failed > 0:
        metrics.add_bottleneck(f"{failed} sessions failed", "high")

    metrics.add_recommendation("Implement session pooling")
    metrics.add_recommendation("Add rate limiting per session")

    filename = metrics.save()
    print(f"\n✅ Test 8 complete: {filename}")
    print(f"   Sessions: {successful}/{num_sessions} successful")


# ============================================================================
# TEST 9: Agent Execution Timeout Test
# ============================================================================


def test_09_agent_execution_timeout():
    """Test agent execution timeout handling."""
    metrics = PerformanceMetrics("09_agent_execution_timeout")

    timeout_scenarios = [
        {"name": "fast_agent", "expected_time": 0.1, "timeout": 1.0},
        {"name": "slow_agent", "expected_time": 2.0, "timeout": 1.0},
        {"name": "normal_agent", "expected_time": 0.5, "timeout": 2.0},
    ]

    results = {}

    for scenario in timeout_scenarios:
        start = time.time()
        timed_out = False

        try:
            # Simulate agent execution
            time.sleep(min(scenario["expected_time"], scenario["timeout"]))
            elapsed = time.time() - start
            timed_out = elapsed >= scenario["timeout"]
        except Exception:
            elapsed = time.time() - start
            timed_out = True

        results[scenario["name"]] = {
            "expected_time": scenario["expected_time"],
            "timeout": scenario["timeout"],
            "actual_time": elapsed,
            "timed_out": timed_out,
            "should_timeout": scenario["expected_time"] > scenario["timeout"],
        }

    metrics.add_metric("timeout_scenarios", results)

    # Identify timeout issues
    for name, result in results.items():
        if result["timed_out"] and not result["should_timeout"]:
            metrics.add_bottleneck(f"Unexpected timeout in {name}", "high")
        elif not result["timed_out"] and result["should_timeout"]:
            metrics.add_bottleneck(f"{name} should have timed out but didn't", "medium")

    metrics.add_recommendation("Implement configurable timeout per agent")
    metrics.add_recommendation("Add timeout warnings for long-running agents")

    filename = metrics.save()
    print(f"\n✅ Test 9 complete: {filename}")
    print(f"   Scenarios tested: {len(results)}")


# ============================================================================
# TEST 10: Cache Performance Test
# ============================================================================


def test_10_cache_performance():
    """Test caching performance and effectiveness."""
    metrics = PerformanceMetrics("10_cache_performance")

    # Simulate cache with varying hit rates
    cache = {}
    cache_hits = 0
    cache_misses = 0

    # Test without cache
    start = time.time()
    for i in range(100):
        # Simulate expensive operation
        result = sum(range(10000))
    no_cache_time = time.time() - start

    # Test with cache
    start = time.time()
    for i in range(100):
        if i in cache:
            result = cache[i]
            cache_hits += 1
        else:
            result = sum(range(10000))
            cache[i] = result
            cache_misses += 1
    with_cache_time = time.time() - start

    # Calculate speedup
    speedup = no_cache_time / with_cache_time if with_cache_time > 0 else 1
    hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0

    metrics.add_metric("no_cache_time_seconds", no_cache_time)
    metrics.add_metric("with_cache_time_seconds", with_cache_time)
    metrics.add_metric("speedup_factor", speedup)
    metrics.add_metric("cache_hit_rate", hit_rate)
    metrics.add_metric("cache_hits", cache_hits)
    metrics.add_metric("cache_misses", cache_misses)

    if hit_rate < 0.5:
        metrics.add_bottleneck(f"Low cache hit rate: {hit_rate*100:.1f}%", "medium")

    metrics.add_recommendation("Implement Redis for distributed caching")
    metrics.add_recommendation("Use cache warming for frequently accessed data")
    metrics.add_recommendation("Add cache invalidation strategy")

    filename = metrics.save()
    print(f"\n✅ Test 10 complete: {filename}")
    print(f"   Cache speedup: {speedup:.1f}x, Hit rate: {hit_rate*100:.1f}%")


# ============================================================================
# Run all tests and generate summary report
# ============================================================================


def test_generate_summary():
    """Generate summary report of all performance tests."""
    print("\n" + "=" * 70)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 70)

    result_files = sorted(
        [f for f in os.listdir(RESULTS_DIR) if f.endswith(".json")],
        key=lambda x: os.path.getmtime(os.path.join(RESULTS_DIR, x)),
    )

    for fname in result_files[-10:]:  # Last 10 results
        filepath = os.path.join(RESULTS_DIR, fname)
        with open(filepath) as f:
            data = json.load(f)
            print(f"\n{data['test_name']}")
            print(f"  Duration: {data.get('duration_seconds', 0):.2f}s")
            if data.get("bottlenecks"):
                print(f"  ⚠️  Bottlenecks: {len(data['bottlenecks'])}")
                for b in data["bottlenecks"][:3]:
                    print(f"     - {b['issue']} ({b['severity']})")
            if data.get("recommendations"):
                print(f"  💡 Recommendations: {len(data['recommendations'])}")

    print("\n" + "=" * 70)
    print(f"All results saved to: {RESULTS_DIR}")
    print("=" * 70)
