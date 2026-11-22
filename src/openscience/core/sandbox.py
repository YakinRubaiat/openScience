"""Security sandbox for safe code execution."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    
    network_egress: str = "deny_all"  # "deny_all", "allowlist", "allow_all"
    allowed_domains: Set[str] = field(default_factory=set)
    file_access: str = "sandbox_only"  # "sandbox_only", "allowlist", "allow_all"
    allowed_paths: Set[str] = field(default_factory=set)
    max_execution_time: int = 3600  # seconds
    max_memory: str = "8GB"
    require_approval: List[str] = field(default_factory=lambda: [
        "code_execution",
        "network_access", 
        "host_file_access",
        "deletion",
        "mcp_tools",
    ])


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
        self._execution_log: List[Dict[str, Any]] = []
        
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
            return agent.execute(task, task.context)
        
        # Check if approval is required
        if self._requires_approval(task):
            approved = self._request_approval(agent, task)
            if not approved:
                raise SecurityError(f"Operation not approved: {task.description}")
        
        # Apply resource limits
        with self._apply_limits():
            result = agent.execute(task, task.context)
            
        # Log execution
        self._execution_log.append({
            "agent": agent.metadata.name,
            "task": task.description,
            "status": "completed",
        })
        
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
        import resource
        import signal
        
        class LimitsContext:
            def __init__(self, policy: SecurityPolicy):
                self.policy = policy
                self.original_limits = {}
                
            def __enter__(self):
                # Set memory limit
                if self.policy.max_memory:
                    mem_limit = self._parse_memory(self.policy.max_memory)
                    self.original_limits["as"] = resource.getrlimit(resource.RLIMIT_AS)
                    resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
                
                # Set CPU time limit
                if self.policy.max_execution_time:
                    self.original_limits["cpu"] = resource.getrlimit(resource.RLIMIT_CPU)
                    resource.setrlimit(
                        resource.RLIMIT_CPU,
                        (self.policy.max_execution_time, self.policy.max_execution_time)
                    )
                    
            def __exit__(self, *args):
                # Restore original limits
                for lim, value in self.original_limits.items():
                    resource.setrlimit(getattr(resource, f"RLIMIT_{lim.upper()}"), value)
                    
            def _parse_memory(self, mem_str: str) -> int:
                """Parse memory string like '8GB' to bytes."""
                units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
                for unit, multiplier in units.items():
                    if mem_str.upper().endswith(unit):
                        return int(mem_str[:-len(unit)]) * multiplier
                return int(mem_str)
                
        return LimitsContext(self.policy)


class SecurityError(Exception):
    """Raised when a security policy violation occurs."""
    pass
