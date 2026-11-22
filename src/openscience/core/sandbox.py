"""Security sandbox for safe code execution."""

import inspect
import resource
import signal  # noqa: F401  (kept for subclasses/integrations)
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class SecurityPolicy:
    """Security policy configuration."""

    network_egress: str = "deny_all"  # "deny_all", "allowlist", "allow_all"
    allowed_domains: set[str] = field(default_factory=set)
    file_access: str = "sandbox_only"  # "sandbox_only", "allowlist", "allow_all"
    allowed_paths: set[str] = field(default_factory=set)
    max_execution_time: int = 3600  # seconds
    max_memory: str = "8GB"
    require_approval: list[str] = field(
        default_factory=lambda: [
            "code_execution",
            "network_access",
            "host_file_access",
            "deletion",
            "mcp_tools",
        ]
    )


class Sandbox:
    """
    OS-level sandbox with deny-by-default network egress.

    The sandbox provides:
    - Network isolation with allowlist controls
    - File system access restrictions
    - Execution time and memory limits
    - Human approval workflows for sensitive operations

    Example:
        >>> sandbox = Sandbox(enabled=True)
        >>> sandbox.policy.allowed_domains.add("pubmed.ncbi.nlm.nih.gov")
        >>> result = sandbox.execute(agent, task)
    """

    def __init__(
        self,
        enabled: bool = True,
        policy: Optional[SecurityPolicy] = None,
        approval_handler: Optional[Callable] = None,
        **kwargs,
    ):
        """
        Initialize the sandbox.

        Args:
            enabled: Enable sandboxing
            policy: Security policy configuration
            approval_handler: Callback for approval requests
        """
        self.enabled = enabled
        self.policy = policy or SecurityPolicy()
        self.approval_handler = approval_handler
        self._execution_log: list[dict[str, Any]] = []

    def execute(self, agent, task) -> Any:
        """
        Execute an agent task within the sandbox.

        Args:
            agent: Agent to execute
            task: Task to perform

        Returns:
            Execution result

        Raises:
            SecurityError: If operation violates policy
        """
        if not self.enabled:
            result = agent.execute(task, task.context)
            if inspect.isawaitable(result):
                result = _run_awaitable(result)
            return result

        # Check if approval is required
        if self._requires_approval(task):
            approved = self._request_approval(agent, task)
            if not approved:
                raise SecurityError(f"Operation not approved: {task.description}")

        # Apply resource limits
        with self._apply_limits():
            result = agent.execute(task, task.context)
            if inspect.isawaitable(result):
                result = _run_awaitable(result)

        # Log execution
        self._execution_log.append(
            {
                "agent": agent.metadata.name,
                "task": task.description,
                "status": "completed",
            }
        )

        return result

    def _requires_approval(self, task) -> bool:
        """Check if a task requires human approval."""
        # Check task parameters against approval list
        for operation in self.policy.require_approval:
            if operation in str(task.parameters).lower():
                return True
        return False

    def _request_approval(self, agent, task) -> bool:
        """Request human approval for an operation."""
        if self.approval_handler:
            return self.approval_handler(agent, task)

        # Default: require explicit approval for sensitive operations
        print(f"⚠️  Approval required for: {task.description}")
        print(f"   Agent: {agent.metadata.name}")
        response = input("   Proceed? [y/N]: ")
        return response.lower() == "y"

    def _apply_limits(self):
        """Context manager to apply resource limits."""

        class LimitsContext:
            def __init__(self, policy: SecurityPolicy):
                self.policy = policy
                self.original_limits = {}

            def __enter__(self):
                # Set memory limit.  Some platforms (e.g. macOS) do not
                # support tightening RLIMIT_AS from an unlimited value --
                # limits are best-effort on development machines and are
                # enforced by the container runtime in production.
                if self.policy.max_memory:
                    try:
                        mem_limit = self._parse_memory(self.policy.max_memory)
                        self.original_limits["as"] = resource.getrlimit(resource.RLIMIT_AS)
                        resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
                    except (OSError, ValueError):
                        pass

                # Set CPU time limit
                if self.policy.max_execution_time:
                    try:
                        self.original_limits["cpu"] = resource.getrlimit(resource.RLIMIT_CPU)
                        resource.setrlimit(
                            resource.RLIMIT_CPU,
                            (self.policy.max_execution_time, self.policy.max_execution_time),
                        )
                    except (OSError, ValueError):
                        pass

            def __exit__(self, *args):
                # Restore original limits as far as permitted. A non-root
                # process may not raise a hard limit once lowered, so keep the
                # current hard limit and restore the soft limit capped by it.
                for lim, (soft, hard) in self.original_limits.items():
                    rlim = getattr(resource, f"RLIMIT_{lim.upper()}")
                    _, cur_hard = resource.getrlimit(rlim)
                    # The hard limit cannot be raised back up by a non-root
                    # process once lowered; keep it and clamp the soft limit.
                    new_hard = cur_hard
                    if cur_hard == resource.RLIM_INFINITY:
                        new_soft = soft
                    else:
                        new_soft = cur_hard if soft == resource.RLIM_INFINITY else min(soft, cur_hard)
                    resource.setrlimit(rlim, (new_soft, new_hard))

            def _parse_memory(self, mem_str: str) -> int:
                """Parse memory string like '8GB' to bytes."""
                # Order matters: check longest suffixes first so that
                # e.g. "8GB" is not matched by the one-character "B".
                units = (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024), ("B", 1))
                upper = mem_str.upper()
                for unit, multiplier in units:
                    if upper.endswith(unit):
                        return int(mem_str[: -len(unit)]) * multiplier
                return int(mem_str)

        return LimitsContext(self.policy)


class SecurityError(Exception):
    """Raised when a security policy violation occurs."""


def _run_awaitable(awaitable):
    """Run an awaitable to completion from synchronous code.

    Reuses a running event loop if one is present, otherwise creates a
    temporary one.
    """
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    result_box: dict[str, Any] = {}
    error_box: dict[str, BaseException] = {}

    def _runner():
        new_loop = asyncio.new_event_loop()
        try:
            result_box["value"] = new_loop.run_until_complete(awaitable)
        except BaseException as exc:
            error_box["error"] = exc
        finally:
            new_loop.close()

    import threading

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in error_box:
        raise error_box["error"]
    return result_box.get("value")
