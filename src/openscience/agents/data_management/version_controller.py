"""Data versioning and lineage agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class VersionControllerAgent(BaseAgent):
    """Agent for data versioning and lineage."""

    metadata = AgentMetadata(
        name="version_controller",
        category="data_management",
        description="Data versioning and lineage",
        required_skills=["dvc", "lineage_tracking"],
        input_types=["data"],
        output_types=["versioned_data"],
    )

    async def execute(self, task, context):
        """Run data versioning and lineage."""
        result = await self.run_skill(
            "dvc",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
