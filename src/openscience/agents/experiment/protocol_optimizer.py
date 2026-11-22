"""Experimental protocol optimization agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ProtocolOptimizerAgent(BaseAgent):
    """Agent for experimental protocol optimization."""

    metadata = AgentMetadata(
        name="protocol_optimizer",
        category="experiment",
        description="Experimental protocol optimization",
        required_skills=["bayesian_optimization", "protocol_analysis"],
        input_types=["protocol_parameters"],
        output_types=["optimized_protocol"],
    )

    async def execute(self, task, context):
        """Run experimental protocol optimization."""
        result = await self.run_skill(
            "bayesian_optimization",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
