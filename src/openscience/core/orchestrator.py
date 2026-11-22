"""Agent orchestration and task routing for openScience."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from openscience.core.agent import BaseAgent, AgentMetadata


@dataclass
class Task:
    """A task to be executed by an agent."""
    
    description: str
    parameters: Dict[str, Any]
    context: Dict[str, Any]
    specialist: Optional[str] = None


@dataclass  
class Result:
    """Result from agent execution."""
    
    data: Any
    metadata: Dict[str, Any]
    artifacts: List[str]


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
        agent_registry: Optional[Dict[str, Type[BaseAgent]]] = None,
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
        self.agents = agent_registry or self._load_agents()
        self._agent_cache: Dict[str, BaseAgent] = {}
        
    def execute_task(
        self,
        task_description: str,
        specialist: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
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
            
        return result
    
    def execute_agent(
        self,
        agent_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
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
            return self.sandbox.execute(agent, task)
        else:
            return agent.execute(task, context)
    
    def answer_question(
        self,
        question: str,
        context: Dict[str, Any],
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
        return self.execute_agent(
            "lit_summarizer",
            parameters={"question": question, "mode": "qa"},
            context=context,
        ).data
    
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
        
        # Default to general analysis
        return self._get_agent_instance(self.agents["qc_analyzer"])
    
    def _get_agent_instance(self, agent_class: Type[BaseAgent]) -> BaseAgent:
        """Get or create an agent instance."""
        name = agent_class.metadata.name
        if name not in self._agent_cache:
            self._agent_cache[name] = agent_class(orchestrator=self)
        return self._agent_cache[name]
    
    def _load_agents(self) -> Dict[str, Type[BaseAgent]]:
        """Load all agent classes from the agents package."""
        import importlib
        import pkgutil
        from openscience import agents
        
        registry = {}
        
        for category in pkgutil.iter_modules(agents.__path__):
            category_module = importlib.import_module(f"openscience.agents.{category.name}")
            
            for agent_info in pkgutil.iter_modules(category_module.__path__):
                agent_module = importlib.import_module(
                    f"openscience.agents.{category.name}.{agent_info.name}"
                )
                
                # Find agent class in module
                for attr_name in dir(agent_module):
                    attr = getattr(agent_module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseAgent)
                        and attr is not BaseAgent
                    ):
                        registry[attr.metadata.name] = attr
                        
        return registry
