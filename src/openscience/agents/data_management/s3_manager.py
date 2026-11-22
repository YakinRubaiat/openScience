"""Cloud storage management agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class S3ManagerAgent(BaseAgent):
    """Agent for cloud storage management."""

    metadata = AgentMetadata(
        name="s3_manager",
        category="data_management",
        description="Cloud storage management",
        required_skills=["boto3", "cloud_storage"],
        input_types=["local_files"],
        output_types=["cloud_locations"],
    )

    async def execute(self, task, context):
        """Run cloud storage management."""
        result = await self.run_skill(
            "boto3",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
