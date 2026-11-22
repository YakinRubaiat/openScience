"""Multi-format data import agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DataIngestorAgent(BaseAgent):
    """Agent for importing data from various file formats."""

    metadata = AgentMetadata(
        name="data_ingestor",
        category="data_management",
        description="Multi-format data import",
        required_skills=["pandas", "anndata", "bioio"],
        input_types=["file_path", "format_hint"],
        output_types=["dataframe", "anndata", "metadata"],
    )

    async def execute(self, task, context):
        """Import data from file."""
        file_path = task.parameters.get("file_path")
        format_hint = task.parameters.get("format_hint", "auto")

        if format_hint == "auto":
            format_hint = self.detect_format(file_path)

        data = await self.run_skill(
            "bioio",
            operation="load",
            file_path=file_path,
            format=format_hint,
        )

        return self.format_result({"data": data, "format": format_hint})
