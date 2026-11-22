"""File format conversion agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class FormatConverterAgent(BaseAgent):
    """Agent for file format conversion."""

    metadata = AgentMetadata(
        name="format_converter",
        category="data_management",
        description="File format conversion",
        required_skills=["format_converters", "data_validation"],
        input_types=["source_format"],
        output_types=["converted_data"],
    )

    async def execute(self, task, context):
        """Run file format conversion."""
        result = await self.run_skill(
            "format_converters",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
