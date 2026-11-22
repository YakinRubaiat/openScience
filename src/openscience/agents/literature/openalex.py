"""Open bibliographic database agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class OpenalexAgent(BaseAgent):
    """Agent for open bibliographic database."""

    metadata = AgentMetadata(
        name="openalex",
        category="literature",
        description="Open bibliographic database",
        required_skills=["openalex_api", "bibliometric_analysis"],
        input_types=["query"],
        output_types=["work_list"],
    )

    async def execute(self, task, context):
        """Run open bibliographic database."""
        result = await self.run_skill(
            "openalex_api",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
