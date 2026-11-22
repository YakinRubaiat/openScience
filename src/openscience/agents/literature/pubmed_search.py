"""PubMed/PMC systematic literature search agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PubMedSearchAgent(BaseAgent):
    """Agent for systematic PubMed and PMC literature searches."""

    metadata = AgentMetadata(
        name="pubmed_search",
        category="literature",
        description="PubMed/PMC systematic literature search",
        required_skills=["pubmed_api", "xml_parsing"],
        input_types=["search_query", "date_range"],
        output_types=["paper_list", "abstracts", "citations"],
    )

    async def execute(self, task, context):
        """Execute a PubMed literature search."""
        query = task.parameters.get("query", "")
        max_results = task.parameters.get("max_results", 100)
        date_from = task.parameters.get("date_from")
        date_to = task.parameters.get("date_to")

        results = await self.run_skill(
            "pubmed_api",
            operation="search",
            query=query,
            max_results=max_results,
            date_from=date_from,
            date_to=date_to,
        )

        return self.format_result(
            {
                "papers": results,
                "count": len(results),
                "query": query,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
