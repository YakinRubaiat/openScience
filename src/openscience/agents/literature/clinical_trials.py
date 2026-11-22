"""Clinical trial registry search agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ClinicalTrialsAgent(BaseAgent):
    """Agent for clinical trial registry search."""

    metadata = AgentMetadata(
        name="clinical_trials",
        category="literature",
        description="Clinical trial registry search",
        required_skills=["clinicaltrials_api", "trial_parser"],
        input_types=["condition"],
        output_types=["trial_list"],
    )

    async def execute(self, task, context):
        """Run clinical trial registry search."""
        result = await self.run_skill(
            "clinicaltrials_api",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
