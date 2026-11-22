"""Variant detection and annotation agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class VariantCallerAgent(BaseAgent):
    """Agent for variant detection and annotation."""

    metadata = AgentMetadata(
        name="variant_caller",
        category="analysis",
        description="Variant detection and annotation",
        required_skills=["gatk", "vep"],
        input_types=["bam_files"],
        output_types=["vcf_file"],
    )

    async def execute(self, task, context):
        """Run variant detection and annotation."""
        result = await self.run_skill(
            "gatk",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
