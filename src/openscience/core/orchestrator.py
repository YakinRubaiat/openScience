"""Agent orchestration and task routing for openScience."""

import inspect
from dataclasses import dataclass
from typing import Any, Optional

from openscience.core.agent import BaseAgent
from openscience.core.sandbox import _run_awaitable


@dataclass
class Task:
    """A task to be executed by an agent."""

    description: str
    parameters: dict[str, Any]
    context: dict[str, Any]
    specialist: Optional[str] = None


@dataclass
class Result:
    """Result from agent execution."""

    data: Any
    metadata: dict[str, Any]
    artifacts: list[str]

    @classmethod
    def coerce(cls, value: Any) -> "Result":
        """Coerce an agent return value into a :class:`Result`."""
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            known = {k: value[k] for k in ("data", "metadata", "artifacts") if k in value}
            metadata = dict(known.get("metadata") or {})
            if "agent" in value:
                metadata.setdefault("agent", value.get("agent"))
            if "data" in value:
                data = value["data"]
                if set(value.keys()) - {"data", "metadata", "artifacts", "agent"}:
                    metadata.setdefault(
                        "extra",
                        {
                            k: v
                            for k, v in value.items()
                            if k not in {"data", "metadata", "artifacts", "agent"}
                        },
                    )
            else:
                data = {k: v for k, v in value.items() if k != "metadata"}
            return cls(data=data, metadata=metadata, artifacts=list(known.get("artifacts") or []))
        return cls(data=value, metadata={}, artifacts=[])


class AgentOrchestrator:
    """
    Central orchestrator for agent selection and task execution.

    The orchestrator routes natural language tasks to appropriate
    specialized agents, manages compute resources, and enforces
    security policies through the sandbox.
    """

    def __init__(
        self,
        sandbox: Optional[Any] = None,
        compute_backend: str = "local",
        agent_registry: Optional[dict[str, type[BaseAgent]]] = None,
        **kwargs,
    ):
        """
        Initialize the orchestrator.

        Args:
            sandbox: Security sandbox for execution control
            compute_backend: Default compute backend
            agent_registry: Custom agent registry (loads default if None)
        """
        self.sandbox = sandbox
        self.compute_backend = compute_backend
        # Use `is None` rather than truthiness so callers can intentionally
        # pass an empty registry without triggering the default loader.
        self.agents = agent_registry if agent_registry is not None else self._load_agents()
        self._agent_cache: dict[str, BaseAgent] = {}
        # Load built-in skill implementations so execute_skill can resolve them.
        try:
            from openscience.skills import load_default_skills

            load_default_skills()
        except Exception:  # pragma: no cover - skills are optional
            pass

    def execute_task(
        self,
        task_description: str,
        specialist: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> Result:
        """
        Execute a natural language task.

        Args:
            task_description: Natural language task description
            specialist: Specific agent name (auto-selected if None)
            parameters: Task parameters
            context: Execution context

        Returns:
            Task execution result
        """
        task = Task(
            description=task_description,
            parameters=parameters or {},
            context=context or {},
            specialist=specialist,
        )

        # Select appropriate agent
        agent = self._select_agent(task)

        # Execute with sandboxing
        if self.sandbox:
            result = self.sandbox.execute(agent, task)
        else:
            result = agent.execute(task, task.context)
            if inspect.isawaitable(result):
                result = _run_awaitable(result)

        return Result.coerce(result)

    def execute_agent(
        self,
        agent_name: str,
        parameters: dict[str, Any],
        context: dict[str, Any],
    ) -> Result:
        """
        Execute a specific agent directly.

        Args:
            agent_name: Name of the agent
            parameters: Agent parameters
            context: Execution context

        Returns:
            Agent execution result
        """
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")

        agent_class = self.agents[agent_name]
        agent = self._get_agent_instance(agent_class)

        task = Task(
            description=f"Direct execution of {agent_name}",
            parameters=parameters,
            context=context,
            specialist=agent_name,
        )

        if self.sandbox:
            return Result.coerce(self.sandbox.execute(agent, task))

        result = agent.execute(task, context)
        if inspect.isawaitable(result):
            result = _run_awaitable(result)
        return Result.coerce(result)

    def execute_skill(self, skill_name: str, operation: str, **kwargs) -> Any:
        """
        Execute a skill (tool) required by an agent.

        The default implementation provides lightweight, deterministic
        responses for the built-in stub skills. Deployments can subclass
        :class:`AgentOrchestrator` to bind real tool implementations.

        Args:
            skill_name: Name of the skill/provider (e.g. "scanpy", "pubmed_api")
            operation: Operation to perform
            **kwargs: Operation-specific arguments

        Returns:
            Skill execution result
        """
        try:
            from openscience import skills as skill_registry
        except Exception:
            skill_registry = None

        if skill_registry is not None:
            fn = skill_registry.get_skill(skill_name)
            if fn is not None:
                return fn(operation=operation, **kwargs)

        # Fallback: deterministic stub echo when no skill is registered.
        return {
            "skill": skill_name,
            "operation": operation,
            "status": "ok",
            "data": kwargs,
        }

    def answer_question(
        self,
        question: str,
        context: dict[str, Any],
    ) -> str:
        """
        Answer a natural language question using available data.

        Args:
            question: Natural language question
            context: Available context (data, results, etc.)

        Returns:
            Natural language answer
        """
        # Use lit_summarizer or related agent for question answering
        agent_name = (
            "lit_summarizer" if "lit_summarizer" in self.agents else next(iter(self.agents), None)
        )
        if agent_name is None:
            return "No agents available to answer the question."
        return str(
            self.execute_agent(
                agent_name,
                parameters={"question": question, "mode": "qa"},
                context=context,
            ).data
        )

    def _select_agent(self, task: Task) -> BaseAgent:
        """
        Select the most appropriate agent for a task.

        Uses agent metadata, task description analysis, and user
        preferences to route tasks optimally.
        """
        if task.specialist:
            agent_class = self.agents.get(task.specialist)
            if not agent_class:
                raise ValueError(f"Unknown specialist: {task.specialist}")
            return self._get_agent_instance(agent_class)

        # Simple keyword-based routing (would use ML in production)
        description = task.description.lower()

        # Map keywords to agents
        keyword_map = {
            "quality control": "qc_analyzer",
            "qc": "qc_analyzer",
            "clustering": "scanpy_specialist",
            "single cell": "scanpy_specialist",
            "rna-seq": "deseq2_specialist",
            "differential expression": "deseq2_specialist",
            "literature": "pubmed_search",
            "papers": "pubmed_search",
            "figure": "matplotlib_stylist",
            "plot": "matplotlib_stylist",
            "write": "abstract_writer",
            "methods": "methods_writer",
        }

        for keyword, agent_name in keyword_map.items():
            if keyword in description:
                agent_class = self.agents.get(agent_name)
                if agent_class:
                    return self._get_agent_instance(agent_class)

        # Default to general analysis agent when available
        if "qc_analyzer" in self.agents:
            return self._get_agent_instance(self.agents["qc_analyzer"])
        if self.agents:
            return self._get_agent_instance(next(iter(self.agents.values())))
        raise ValueError("No agents available to handle the task")

    def _get_agent_instance(self, agent_class: type[BaseAgent]) -> BaseAgent:
        """Get or create an agent instance."""
        name = agent_class.metadata.name
        if name not in self._agent_cache:
            self._agent_cache[name] = agent_class(orchestrator=self)
        return self._agent_cache[name]

    def _load_agents(self) -> dict[str, type[BaseAgent]]:
        """Load all agent classes from the agents package."""
        import importlib
        import pkgutil

        from openscience import agents

        registry = {}

        for category in pkgutil.iter_modules(agents.__path__):
            try:
                category_module = importlib.import_module(f"openscience.agents.{category.name}")
            except Exception:
                continue

            for agent_info in pkgutil.iter_modules(category_module.__path__):
                try:
                    agent_module = importlib.import_module(
                        f"openscience.agents.{category.name}.{agent_info.name}"
                    )
                except Exception:
                    # Skip broken or non-importable agent modules.
                    continue

                # Find agent class in module
                for attr_name in dir(agent_module):
                    attr = getattr(agent_module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseAgent)
                        and attr is not BaseAgent
                        and hasattr(attr, "metadata")
                    ):
                        registry[attr.metadata.name] = attr

        return registry
