"""Quality and integrity checking agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DataValidatorAgent(BaseAgent):
    """Agent for quality and integrity checking."""

    metadata = AgentMetadata(
        name="data_validator",
        category="data_management",
        description="Quality and integrity checking",
        required_skills=["data_validation", "integrity_checks"],
        input_types=["dataset"],
        output_types=["validation_report"],
    )

    async def execute(self, task, context):
        """Run quality and integrity checking."""
        result = await self.run_skill(
            "data_validation",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
