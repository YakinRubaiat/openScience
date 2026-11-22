"""Metadata extraction and validation agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class MetadataExtractorAgent(BaseAgent):
    """Agent for metadata extraction and validation."""

    metadata = AgentMetadata(
        name="metadata_extractor",
        category="data_management",
        description="Metadata extraction and validation",
        required_skills=["metadata_standards", "validation_rules"],
        input_types=["raw_data"],
        output_types=["metadata"],
    )

    async def execute(self, task, context):
        """Run metadata extraction and validation."""
        result = await self.run_skill(
            "metadata_standards",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
