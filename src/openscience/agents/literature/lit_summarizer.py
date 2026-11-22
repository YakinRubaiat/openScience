"""Automated literature summarization agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class LitSummarizerAgent(BaseAgent):
    """Agent for automated literature summarization."""

    metadata = AgentMetadata(
        name="lit_summarizer",
        category="literature",
        description="Automated literature summarization",
        required_skills=["llm_summarization", "citation_extraction"],
        input_types=["paper_text"],
        output_types=["summary"],
    )

    async def execute(self, task, context):
        """Run automated literature summarization."""
        result = await self.run_skill(
            "llm_summarization",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
