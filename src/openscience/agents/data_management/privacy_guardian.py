"""PHI/PII detection and masking agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PrivacyGuardianAgent(BaseAgent):
    """Agent for pHI/PII detection and masking."""

    metadata = AgentMetadata(
        name="privacy_guardian",
        category="data_management",
        description="PHI/PII detection and masking",
        required_skills=["pii_detection", "anonymization"],
        input_types=["sensitive_data"],
        output_types=["masked_data"],
    )

    async def execute(self, task, context):
        """Run pHI/PII detection and masking."""
        result = await self.run_skill(
            "pii_detection",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
