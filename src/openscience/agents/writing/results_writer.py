"""Results narrative generation agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ResultsWriterAgent(BaseAgent):
    """Agent for results narrative generation."""

    metadata = AgentMetadata(
        name="results_writer",
        category="writing",
        description="Results narrative generation",
        required_skills=["results_writing", "statistical_reporting"],
        input_types=["analysis_results"],
        output_types=["results_section"],
    )

    async def execute(self, task, context):
        """Run results narrative generation."""
        result = await self.run_skill(
            "results_writing",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
