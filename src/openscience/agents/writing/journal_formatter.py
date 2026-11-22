"""Journal-specific submission formatting agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class JournalFormatterAgent(BaseAgent):
    """Agent for journal-specific submission formatting."""

    metadata = AgentMetadata(
        name="journal_formatter",
        category="writing",
        description="Journal-specific submission formatting",
        required_skills=["journal_templates", "formatting_rules"],
        input_types=["manuscript"],
        output_types=["formatted_manuscript"],
    )

    async def execute(self, task, context):
        """Run journal-specific submission formatting."""
        result = await self.run_skill(
            "journal_templates",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
