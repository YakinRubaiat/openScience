"""Scientific schematic creation agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class SchematicIllustratorAgent(BaseAgent):
    """Agent for scientific schematic creation."""

    metadata = AgentMetadata(
        name="schematic_illustrator",
        category="visualization",
        description="Scientific schematic creation",
        required_skills=["matplotlib", "illustration_tools"],
        input_types=["description"],
        output_types=["schematic"],
    )

    async def execute(self, task, context):
        """Run scientific schematic creation."""
        result = await self.run_skill(
            "matplotlib",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
