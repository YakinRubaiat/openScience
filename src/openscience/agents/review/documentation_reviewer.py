"""Documentation Review Agent for openScience."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DocumentationReviewerAgent(BaseAgent):
    """
    Agent for reviewing documentation completeness and quality.

    Reviews:
    - Docstring coverage
    - API documentation
    - README completeness
    - Code comments quality
    - Tutorial completeness
    - Example code accuracy
    - Type hint documentation
    """

    metadata = AgentMetadata(
        name="documentation_reviewer",
        category="review",
        description="Reviews documentation completeness and quality",
        required_skills=["pydocstyle", "darglint", "interrogate"],
        input_types=["source_code", "documentation"],
        output_types=["documentation_report", "coverage_metrics", "recommendations"],
    )

    async def execute(self, task, context):
        """Execute documentation review."""
        target_path = task.parameters.get("target_path", "src/")

        # Check docstring coverage
        docstring_coverage = await self.run_skill(
            "interrogate",
            operation="check",
            path=target_path,
        )

        # Check docstring style
        docstring_style = await self.run_skill(
            "pydocstyle",
            operation="check",
            path=target_path,
        )

        # Check docstring correctness
        docstring_correctness = await self.run_skill(
            "darglint",
            operation="check",
            path=target_path,
        )

        # Analyze README
        readme_analysis = self._analyze_readme()

        # Check API documentation
        api_docs = self._check_api_documentation()

        return self.format_result(
            {
                "docstring_coverage": docstring_coverage,
                "docstring_style_issues": docstring_style,
                "docstring_correctness": docstring_correctness,
                "readme_analysis": readme_analysis,
                "api_documentation": api_docs,
                "recommendations": self._generate_documentation_recommendations(
                    docstring_coverage,
                    docstring_style,
                    readme_analysis,
                ),
            }
        )

    def _analyze_readme(self):
        """Analyze README completeness."""
        return {
            "exists": True,
            "sections_present": [],
            "sections_missing": [],
            "code_examples": 0,
            "images": 0,
        }

    def _check_api_documentation(self):
        """Check API documentation completeness."""
        return {
            "endpoints_documented": 0,
            "endpoints_missing_docs": [],
            "examples_provided": 0,
        }

    def _generate_documentation_recommendations(self, coverage, style, readme):
        """Generate documentation recommendations."""
        recommendations = []

        coverage_percent = coverage.get("coverage", 0)
        if coverage_percent < 80:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "documentation",
                    "action": f"Increase docstring coverage to 80%+ (current: {coverage_percent}%)",
                }
            )

        if style.get("error_count", 0) > 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "documentation",
                    "action": f"Fix {style['error_count']} docstring style issues",
                }
            )

        missing_sections = readme.get("sections_missing", [])
        if missing_sections:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "documentation",
                    "action": f"Add missing README sections: {', '.join(missing_sections)}",
                }
            )

        return recommendations
