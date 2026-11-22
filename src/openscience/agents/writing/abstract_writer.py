"""Abstract drafting and optimization agent."""

from openscience.core.agent import BaseAgent, AgentMetadata


class AbstractWriterAgent(BaseAgent):
    """Agent for drafting and optimizing scientific abstracts."""

    metadata = AgentMetadata(
        name="abstract_writer",
        category="writing",
        description="Abstract drafting and optimization",
        required_skills=["text_summarization", "scientific_writing"],
        input_types=["paper_content", "target_journal"],
        output_types=["abstract_draft", "word_count_analysis"],
    )

    async def execute(self, task, context):
        """Draft a scientific abstract."""
        content = task.parameters.get("paper_content", "")
        journal = task.parameters.get("target_journal", "general")
        word_limit = task.parameters.get("word_limit", 250)

        abstract = await self.run_skill(
            "scientific_writing",
            operation="write_abstract",
            content=content,
            journal=journal,
            word_limit=word_limit,
        )

        return self.format_result(abstract)
