"""USPTO/EPO patent literature agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PatentSearchAgent(BaseAgent):
    """Agent for uSPTO/EPO patent literature."""

    metadata = AgentMetadata(
        name="patent_search",
        category="literature",
        description="USPTO/EPO patent literature",
        required_skills=["patent_api", "patent_parser"],
        input_types=["invention_query"],
        output_types=["patent_list"],
    )

    async def execute(self, task, context):
        """Run uSPTO/EPO patent literature."""
        result = await self.run_skill(
            "patent_api",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
