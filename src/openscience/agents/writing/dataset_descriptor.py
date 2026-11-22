"""Data availability statements agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DatasetDescriptorAgent(BaseAgent):
    """Agent for data availability statements."""

    metadata = AgentMetadata(
        name="dataset_descriptor",
        category="writing",
        description="Data availability statements",
        required_skills=["data_description", "repository_documentation"],
        input_types=["dataset_metadata"],
        output_types=["availability_statement"],
    )

    async def execute(self, task, context):
        """Run data availability statements."""
        result = await self.run_skill(
            "data_description",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
