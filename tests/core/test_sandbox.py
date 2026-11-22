"""Tests for openscience.core.sandbox — SecurityPolicy, Sandbox, SecurityError."""

from unittest.mock import MagicMock, patch

import pytest

from openscience.core.agent import AgentMetadata, BaseAgent
from openscience.core.orchestrator import Task
from openscience.core.sandbox import Sandbox, SecurityError, SecurityPolicy

# ---------------------------------------------------------------------------
# Concrete agent stubs
# ---------------------------------------------------------------------------


class SimpleAgent(BaseAgent):
    metadata = AgentMetadata(name="simple", category="t", description="d")

    async def execute(self, task, context):
        return {"status": "ok"}


class CodeExecAgent(BaseAgent):
    metadata = AgentMetadata(name="code_exec", category="t", description="d")

    async def execute(self, task, context):
        return {"code_executed": True}


def _make_task(description="test", parameters=None, context=None):
    return Task(
        description=description,
        parameters=parameters or {},
        context=context or {},
    )


# ===================================================================
# SecurityPolicy
# ===================================================================


class TestSecurityPolicy:
    """Tests for the SecurityPolicy dataclass."""

    def test_defaults(self):
        p = SecurityPolicy()
        assert p.network_egress == "deny_all"
        assert p.allowed_domains == set()
        assert p.file_access == "sandbox_only"
        assert p.allowed_paths == set()
        assert p.max_execution_time == 3600
        assert p.max_memory == "8GB"

    def test_default_require_approval_list(self):
        p = SecurityPolicy()
        expected = {
            "code_execution",
            "network_access",
            "host_file_access",
            "deletion",
            "mcp_tools",
        }
        assert set(p.require_approval) == expected

    def test_require_approval_not_shared(self):
        """Mutable default list is not shared between instances."""
        p1 = SecurityPolicy()
        p2 = SecurityPolicy()
        p1.require_approval.append("extra")
        assert "extra" not in p2.require_approval

    def test_allowed_domains_not_shared(self):
        p1 = SecurityPolicy()
        p2 = SecurityPolicy()
        p1.allowed_domains.add("example.com")
        assert "example.com" not in p2.allowed_domains

    def test_custom_values(self):
        p = SecurityPolicy(
            network_egress="allowlist",
            allowed_domains={"pubmed.gov"},
            file_access="allowlist",
            allowed_paths={"/data"},
            max_execution_time=600,
            max_memory="4GB",
            require_approval=["deletion"],
        )
        assert p.network_egress == "allowlist"
        assert "pubmed.gov" in p.allowed_domains
        assert p.file_access == "allowlist"
        assert p.max_execution_time == 600
        assert p.max_memory == "4GB"

    def test_allowed_paths_not_shared(self):
        p1 = SecurityPolicy()
        p2 = SecurityPolicy()
        p1.allowed_paths.add("/tmp")
        assert "/tmp" not in p2.allowed_paths


# ===================================================================
# SecurityError
# ===================================================================


class TestSecurityError:
    """Tests for the SecurityError exception."""

    def test_is_exception(self):
        assert issubclass(SecurityError, Exception)

    def test_raise_and_catch(self):
        with pytest.raises(SecurityError, match="test violation"):
            raise SecurityError("test violation")

    def test_message(self):
        err = SecurityError("denied")
        assert str(err) == "denied"


# ===================================================================
# Sandbox — Initialisation
# ===================================================================


class TestSandboxInit:
    """Tests for Sandbox construction."""

    def test_default_enabled(self):
        sb = Sandbox()
        assert sb.enabled is True

    def test_disabled(self):
        sb = Sandbox(enabled=False)
        assert sb.enabled is False

    def test_default_policy(self):
        sb = Sandbox()
        assert isinstance(sb.policy, SecurityPolicy)

    def test_custom_policy(self):
        policy = SecurityPolicy(max_memory="2GB")
        sb = Sandbox(policy=policy)
        assert sb.policy.max_memory == "2GB"

    def test_approval_handler_stored(self):
        handler = lambda a, t: True
        sb = Sandbox(approval_handler=handler)
        assert sb.approval_handler is handler

    def test_execution_log_starts_empty(self):
        sb = Sandbox()
        assert sb._execution_log == []

    def test_no_approval_handler_by_default(self):
        sb = Sandbox()
        assert sb.approval_handler is None


# ===================================================================
# Sandbox — execute() passthrough when disabled
# ===================================================================


class TestSandboxExecuteDisabled:
    """When sandbox is disabled, execute passes straight through."""

    def test_disabled_sandbox_calls_agent_execute(self):
        agent = SimpleAgent()
        task = _make_task("do something")
        sb = Sandbox(enabled=False)
        result = sb.execute(agent, task)
        # asyncio.run needed because agent.execute is a coroutine
        assert result is not None  # Will be a coroutine

    def test_disabled_sandbox_does_not_log(self):
        agent = SimpleAgent()
        task = _make_task("do something")
        sb = Sandbox(enabled=False)
        sb.execute(agent, task)
        assert sb._execution_log == []

    def test_disabled_sandbox_no_approval(self):
        """Approval is never requested when disabled."""
        handler = MagicMock(return_value=False)
        sb = Sandbox(enabled=False, approval_handler=handler)
        agent = SimpleAgent()
        task = _make_task("test", parameters={"deletion": True})
        sb.execute(agent, task)
        handler.assert_not_called()


# ===================================================================
# Sandbox — execute() with approval workflow
# ===================================================================


class TestSandboxExecuteApproval:
    """Tests for the approval workflow in Sandbox.execute."""

    def test_approval_granted(self):
        handler = MagicMock(return_value=True)
        sb = Sandbox(enabled=True, approval_handler=handler)
        agent = SimpleAgent()
        # "code_execution" appears in require_approval
        task = _make_task("run code", parameters={"code_execution": True})
        # We need to run the coroutine part; the sandbox calls agent.execute()
        # which is async, but sandbox itself is sync — we'll patch _apply_limits
        # to avoid resource limit complexity in tests.
        with patch.object(Sandbox, "_apply_limits") as mock_limits:
            mock_limits.return_value.__enter__ = MagicMock()
            mock_limits.return_value.__exit__ = MagicMock(return_value=False)
            result = sb.execute(agent, task)

        handler.assert_called_once()
        assert result is not None  # Should be coroutine result

    def test_approval_denied_raises_security_error(self):
        handler = MagicMock(return_value=False)
        sb = Sandbox(enabled=True, approval_handler=handler)
        agent = SimpleAgent()
        task = _make_task("delete files", parameters={"deletion": True})
        with pytest.raises(SecurityError, match="not approved"):
            sb.execute(agent, task)

    def test_no_approval_needed(self):
        """A task with no sensitive keywords skips approval."""
        handler = MagicMock(return_value=True)
        sb = Sandbox(enabled=True, approval_handler=handler)
        agent = SimpleAgent()
        task = _make_task("harmless", parameters={"some": "data"})
        with patch.object(Sandbox, "_apply_limits") as mock_limits:
            mock_limits.return_value.__enter__ = MagicMock()
            mock_limits.return_value.__exit__ = MagicMock(return_value=False)
            sb.execute(agent, task)
        handler.assert_not_called()

    def test_approval_keywords_trigger(self):
        """Each keyword in require_approval triggers approval."""
        keywords = [
            "code_execution",
            "network_access",
            "host_file_access",
            "deletion",
            "mcp_tools",
        ]
        for kw in keywords:
            handler = MagicMock(return_value=True)
            sb = Sandbox(enabled=True, approval_handler=handler)
            agent = SimpleAgent()
            task = _make_task("test", parameters={kw: True})
            with patch.object(Sandbox, "_apply_limits") as mock_limits:
                mock_limits.return_value.__enter__ = MagicMock()
                mock_limits.return_value.__exit__ = MagicMock(return_value=False)
                sb.execute(agent, task)
            handler.assert_called_once()

    def test_custom_approval_keywords(self):
        """A custom require_approval list controls which keywords trigger."""
        policy = SecurityPolicy(require_approval=["special_op"])
        handler = MagicMock(return_value=True)
        sb = Sandbox(enabled=True, policy=policy, approval_handler=handler)
        agent = SimpleAgent()

        # This should NOT trigger
        task_safe = _make_task("no trigger", parameters={"code_execution": True})
        with patch.object(Sandbox, "_apply_limits") as mock_limits:
            mock_limits.return_value.__enter__ = MagicMock()
            mock_limits.return_value.__exit__ = MagicMock(return_value=False)
            sb.execute(agent, task_safe)
        handler.assert_not_called()

        # This SHOULD trigger
        task_trigger = _make_task("triggering", parameters={"special_op": True})
        with patch.object(Sandbox, "_apply_limits") as mock_limits:
            mock_limits.return_value.__enter__ = MagicMock()
            mock_limits.return_value.__exit__ = MagicMock(return_value=False)
            sb.execute(agent, task_trigger)
        handler.assert_called_once()


# ===================================================================
# Sandbox — execute() logging
# ===================================================================


class TestSandboxExecutionLog:
    """Tests for execution logging."""

    def test_execution_logged_on_success(self):
        sb = Sandbox(enabled=True, approval_handler=lambda a, t: True)
        agent = SimpleAgent()
        task = _make_task("test task", parameters={"code_execution": True})
        with patch.object(Sandbox, "_apply_limits") as mock_limits:
            mock_limits.return_value.__enter__ = MagicMock()
            mock_limits.return_value.__exit__ = MagicMock(return_value=False)
            sb.execute(agent, task)

        assert len(sb._execution_log) == 1
        entry = sb._execution_log[0]
        assert entry["agent"] == "simple"
        assert entry["task"] == "test task"
        assert entry["status"] == "completed"

    def test_multiple_executions_logged(self):
        sb = Sandbox(enabled=True, approval_handler=lambda a, t: True)
        agent = SimpleAgent()
        for i in range(3):
            task = _make_task(f"task {i}", parameters={"deletion": True})
            with patch.object(Sandbox, "_apply_limits") as mock_limits:
                mock_limits.return_value.__enter__ = MagicMock()
                mock_limits.return_value.__exit__ = MagicMock(return_value=False)
                sb.execute(agent, task)
        assert len(sb._execution_log) == 3

    def test_denied_execution_not_logged(self):
        sb = Sandbox(enabled=True, approval_handler=lambda a, t: False)
        agent = SimpleAgent()
        task = _make_task("denied task", parameters={"deletion": True})
        with pytest.raises(SecurityError):
            sb.execute(agent, task)
        assert len(sb._execution_log) == 0


# ===================================================================
# Sandbox — Resource limits (_apply_limits)
# ===================================================================


class TestApplyLimits:
    """Tests for the _apply_limits context manager."""

    def test_returns_context_manager(self):
        sb = Sandbox(enabled=True)
        ctx = sb._apply_limits()
        assert hasattr(ctx, "__enter__")
        assert hasattr(ctx, "__exit__")

    @patch("openscience.core.sandbox.resource")
    def test_memory_limit_applied(self, mock_resource):
        mock_resource.RLIMIT_AS = 0
        mock_resource.getrlimit.return_value = (-1, -1)
        policy = SecurityPolicy(max_memory="4GB", max_execution_time=60)
        sb = Sandbox(enabled=True, policy=policy)
        ctx = sb._apply_limits()
        ctx.__enter__()
        # Verify setrlimit was called
        assert mock_resource.setrlimit.called
        mock_resource.setrlimit.reset_mock()
        # Restore limits
        mock_resource.getrlimit.return_value = (-1, -1)
        ctx.__exit__()

    @patch("openscience.core.sandbox.resource")
    def test_cpu_limit_applied(self, mock_resource):
        mock_resource.RLIMIT_CPU = 1
        mock_resource.getrlimit.return_value = (-1, -1)
        policy = SecurityPolicy(max_memory="1GB", max_execution_time=300)
        sb = Sandbox(enabled=True, policy=policy)
        ctx = sb._apply_limits()
        ctx.__enter__()
        assert mock_resource.setrlimit.called


# ===================================================================
# Sandbox — _parse_memory
# ===================================================================


class TestParseMemory:
    """Tests for the _parse_memory helper inside _apply_limits."""

    def _parse(self, mem_str: str) -> int:
        """Helper to access _parse_memory."""
        from openscience.core.sandbox import Sandbox

        sb = Sandbox(enabled=True)
        ctx = sb._apply_limits()
        return ctx._parse_memory(mem_str)

    def test_gigabytes(self):
        assert self._parse("8GB") == 8 * 1024**3

    def test_megabytes(self):
        assert self._parse("512MB") == 512 * 1024**2

    def test_kilobytes(self):
        assert self._parse("1024KB") == 1024 * 1024

    def test_bytes(self):
        assert self._parse("1024B") == 1024

    def test_plain_number(self):
        assert self._parse("4096") == 4096

    def test_case_insensitive(self):
        assert self._parse("2gb") == 2 * 1024**3
        assert self._parse("2Gb") == 2 * 1024**3


# ===================================================================
# Sandbox — _request_approval (interactive fallback)
# ===================================================================


class TestRequestApproval:
    """Tests for the _request_approval method."""

    def test_custom_handler_called(self):
        handler = MagicMock(return_value=True)
        sb = Sandbox(enabled=True, approval_handler=handler)
        agent = SimpleAgent()
        task = _make_task("test")
        result = sb._request_approval(agent, task)
        handler.assert_called_once_with(agent, task)
        assert result is True

    def test_custom_handler_false(self):
        handler = MagicMock(return_value=False)
        sb = Sandbox(enabled=True, approval_handler=handler)
        result = sb._request_approval(SimpleAgent(), _make_task("t"))
        assert result is False

    @patch("builtins.input", return_value="y")
    def test_interactive_yes(self, mock_input):
        sb = Sandbox(enabled=True)
        result = sb._request_approval(SimpleAgent(), _make_task("t"))
        assert result is True

    @patch("builtins.input", return_value="n")
    def test_interactive_no(self, mock_input):
        sb = Sandbox(enabled=True)
        result = sb._request_approval(SimpleAgent(), _make_task("t"))
        assert result is False

    @patch("builtins.input", return_value="")
    def test_interactive_empty_default_no(self, mock_input):
        sb = Sandbox(enabled=True)
        result = sb._request_approval(SimpleAgent(), _make_task("t"))
        assert result is False

    @patch("builtins.input", return_value="Y")
    def test_interactive_uppercase_yes(self, mock_input):
        sb = Sandbox(enabled=True)
        result = sb._request_approval(SimpleAgent(), _make_task("t"))
        assert result is True


# ===================================================================
# Sandbox — _requires_approval
# ===================================================================


class TestRequiresApproval:
    """Tests for the _requires_approval detection logic."""

    def test_no_match_returns_false(self):
        sb = Sandbox(enabled=True)
        task = _make_task("safe", parameters={"safe": "data"})
        assert sb._requires_approval(task) is False

    def test_match_in_key(self):
        sb = Sandbox(enabled=True)
        task = _make_task("t", parameters={"code_execution": True})
        assert sb._requires_approval(task) is True

    def test_match_in_value(self):
        sb = Sandbox(enabled=True)
        task = _make_task("t", parameters={"action": "deletion"})
        assert sb._requires_approval(task) is True

    def test_match_in_nested_string(self):
        sb = Sandbox(enabled=True)
        task = _make_task("t", parameters={"desc": "requires network_access to fetch"})
        assert sb._requires_approval(task) is True

    def test_custom_policy_keywords(self):
        policy = SecurityPolicy(require_approval=["custom_op"])
        sb = Sandbox(enabled=True, policy=policy)
        task = _make_task("t", parameters={"custom_op": True})
        assert sb._requires_approval(task) is True

    def test_empty_parameters(self):
        sb = Sandbox(enabled=True)
        task = _make_task("t", parameters={})
        assert sb._requires_approval(task) is False
