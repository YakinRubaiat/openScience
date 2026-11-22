"""Core session management for openScience."""

from pathlib import Path
from typing import Any, Optional, Union

from openscience.core.orchestrator import AgentOrchestrator
from openscience.core.sandbox import Sandbox


class ScienceSession:
    """
    Main entry point for openScience interactions.

    A ScienceSession maintains state across multiple analysis steps,
    manages compute resources, and provides a unified interface to all
    100+ specialized agents.

    Example:
        >>> session = ScienceSession()
        >>> session.load_data("data/pbmc_10k.h5ad")
        >>> result = session.analyze("Quality control and clustering")
        >>> figure = session.visualize(result, type="umap")
    """

    def __init__(
        self,
        project_dir: Optional[Union[str, Path]] = None,
        compute_backend: str = "local",
        sandbox_enabled: bool = True,
        **kwargs,
    ):
        """
        Initialize a new ScienceSession.

        Args:
            project_dir: Root directory for project files
            compute_backend: Default compute backend ("local", "slurm", "ssh", etc.)
            sandbox_enabled: Enable OS-level sandboxing
            **kwargs: Additional configuration options
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.compute_backend = compute_backend
        self.sandbox_enabled = sandbox_enabled

        # Initialize core components
        self.sandbox = Sandbox(enabled=sandbox_enabled) if sandbox_enabled else None
        self.orchestrator = AgentOrchestrator(
            sandbox=self.sandbox,
            compute_backend=compute_backend,
            **kwargs,
        )

        # Session state
        self._data: dict[str, Any] = {}
        self._results: dict[str, Any] = {}
        self._artifacts: list[Path] = []

    def load_data(
        self,
        file_path: Union[str, Path],
        format: str = "auto",
        name: Optional[str] = None,
        **kwargs,
    ) -> "ScienceSession":
        """
        Load data into the session.

        Args:
            file_path: Path to data file
            format: Data format ("auto", "anndata", "csv", "fastq", etc.)
            name: Name to assign to this dataset
            **kwargs: Format-specific loading options

        Returns:
            Self for method chaining
        """
        file_path = Path(file_path)
        if name is None:
            name = file_path.stem

        result = self.orchestrator.execute_agent(
            "data_ingestor",
            parameters={
                "file_path": file_path,
                "format_hint": format,
                **kwargs,
            },
            context=self._build_context(),
        )

        self._data[name] = result.data
        return self

    def analyze(
        self,
        task: str,
        specialist: Optional[str] = None,
        data_name: Optional[str] = None,
        **parameters,
    ) -> Any:
        """
        Run an analysis task.

        Args:
            task: Natural language description of the task
            specialist: Specific agent to use (auto-selected if None)
            data_name: Name of dataset to analyze (uses last loaded if None)
            **parameters: Task-specific parameters

        Returns:
            Analysis results
        """
        context = self._build_context()
        if data_name is None and self._data:
            data_name = list(self._data.keys())[-1]

        if data_name:
            context["data"] = self._data[data_name]

        result = self.orchestrator.execute_task(
            task_description=task,
            specialist=specialist,
            parameters=parameters,
            context=context,
        )

        self._results[task] = result
        return result

    def visualize(
        self,
        result: Any,
        type: str = "auto",
        style: str = "publication",
        output: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> Any:
        """
        Generate visualization from analysis results.

        Args:
            result: Analysis result to visualize
            type: Visualization type ("auto", "umap", "volcano", "heatmap", etc.)
            style: Style preset ("publication", "presentation", "interactive")
            output: Output file path
            **kwargs: Visualization-specific options

        Returns:
            Figure object or file path
        """
        return self.orchestrator.execute_agent(
            "publication_formatter",
            parameters={
                "figure_data": result,
                "viz_type": type,
                "style": style,
                "output_path": output,
                **kwargs,
            },
            context=self._build_context(),
        )

    def write_methods(
        self,
        result: Any,
        style: str = "nature",
        citation_format: str = "apa",
        **kwargs,
    ) -> str:
        """
        Generate methods section text from analysis results.

        Args:
            result: Analysis result to document
            style: Journal style ("nature", "science", "cell", "plos")
            citation_format: Citation format ("apa", "vancouver", "harvard")
            **kwargs: Additional writing options

        Returns:
            Methods section text
        """
        return self.orchestrator.execute_agent(
            "methods_writer",
            parameters={
                "analysis_result": result,
                "journal_style": style,
                "citation_format": citation_format,
                **kwargs,
            },
            context=self._build_context(),
        ).data

    def ask(self, question: str) -> str:
        """
        Ask a natural language question about the data or results.

        Args:
            question: Natural language question

        Returns:
            Answer with supporting evidence
        """
        return self.orchestrator.answer_question(
            question=question,
            context=self._build_context(),
        )

    def _build_context(self) -> dict[str, Any]:
        """Build execution context for agents."""
        return {
            "project_dir": self.project_dir,
            "data": self._data,
            "results": self._results,
            "artifacts": self._artifacts,
            "sandbox": self.sandbox,
        }

    def save(self, path: Union[str, Path]) -> Path:
        """Save session state to disk."""
        import pickle

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "data": self._data,
            "results": self._results,
            "artifacts": self._artifacts,
            "project_dir": self.project_dir,
        }

        with open(path, "wb") as f:
            pickle.dump(state, f)

        return path

    @classmethod
    def load(cls, path: Union[str, Path]) -> "ScienceSession":
        """Load a saved session from disk."""
        import pickle

        path = Path(path)

        with open(path, "rb") as f:
            state = pickle.load(f)

        session = cls(project_dir=state["project_dir"])
        session._data = state["data"]
        session._results = state["results"]
        session._artifacts = state["artifacts"]

        return session
