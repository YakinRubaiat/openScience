"""Identification of understudied areas agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ResearchGapAnalyzerAgent(BaseAgent):
    """Agent for identification of understudied areas."""

    metadata = AgentMetadata(
        name="research_gap_analyzer",
        category="literature",
        description="Identification of understudied areas",
        required_skills=["bibliometric_analysis", "topic_modeling"],
        input_types=["corpus"],
        output_types=["gap_analysis"],
    )

    async def execute(self, task, context):
        """Run identification of understudied areas."""
        result = await self.run_skill(
            "bibliometric_analysis",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
