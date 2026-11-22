"""Outlier detection and cleaning agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DataCleanerAgent(BaseAgent):
    """Agent for outlier detection and cleaning."""

    metadata = AgentMetadata(
        name="data_cleaner",
        category="data_management",
        description="Outlier detection and cleaning",
        required_skills=["outlier_detection", "cleaning_algorithms"],
        input_types=["dirty_data"],
        output_types=["clean_data"],
    )

    async def execute(self, task, context):
        """Run outlier detection and cleaning."""
        result = await self.run_skill(
            "outlier_detection",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
