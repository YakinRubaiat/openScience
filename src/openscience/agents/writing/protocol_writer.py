"""Standard operating procedures agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ProtocolWriterAgent(BaseAgent):
    """Agent for standard operating procedures."""

    metadata = AgentMetadata(
        name="protocol_writer",
        category="writing",
        description="Standard operating procedures",
        required_skills=["protocol_documentation", "sop_writing"],
        input_types=["protocol_steps"],
        output_types=["sop_document"],
    )

    async def execute(self, task, context):
        """Run standard operating procedures."""
        result = await self.run_skill(
            "protocol_documentation",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
