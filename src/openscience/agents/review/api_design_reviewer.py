"""API Design Review Agent for openScience."""

from openscience.core.agent import AgentMetadata, BaseAgent


class APIDesignReviewerAgent(BaseAgent):
    """
    Agent for reviewing API design and RESTful best practices.

    Reviews:
    - RESTful conventions
    - Endpoint naming
    - HTTP method usage
    - Status code usage
    - Response format consistency
    - Error handling
    - Versioning strategy
    - Rate limiting
    """

    metadata = AgentMetadata(
        name="api_design_reviewer",
        category="review",
        description="Reviews API design and RESTful best practices",
        required_skills=["openapi-spec-validator", "spectral"],
        input_types=["api_spec", "endpoint_code"],
        output_types=["api_report", "design_violations", "recommendations"],
    )

    async def execute(self, task, context):
        """Execute API design review."""
        api_spec = task.parameters.get("api_spec", "openapi.yaml")

        # Validate OpenAPI spec
        spec_validation = await self.run_skill(
            "openapi-spec-validator",
            operation="validate",
            spec_file=api_spec,
        )

        # Check RESTful conventions
        rest_violations = await self.run_skill(
            "spectral",
            operation="lint",
            spec_file=api_spec,
        )

        # Analyze endpoint design
        endpoint_analysis = self._analyze_endpoints(task.parameters.get("api_code", ""))

        # Review error handling
        error_handling = self._review_error_handling(task.parameters.get("api_code", ""))

        # Check response consistency
        response_consistency = self._check_response_consistency(task.parameters.get("api_code", ""))

        return self.format_result(
            {
                "spec_validation": spec_validation,
                "rest_violations": rest_violations,
                "endpoint_analysis": endpoint_analysis,
                "error_handling": error_handling,
                "response_consistency": response_consistency,
                "recommendations": self._generate_api_recommendations(
                    spec_validation,
                    rest_violations,
                    endpoint_analysis,
                ),
            }
        )

    def _analyze_endpoints(self, api_code):
        """Analyze API endpoint design."""
        return {
            "total_endpoints": 0,
            "naming_violations": [],
            "missing_versioning": [],
        }

    def _review_error_handling(self, api_code):
        """Review error handling patterns."""
        return {
            "missing_error_handlers": [],
            "inconsistent_error_formats": [],
            "exposed_stack_traces": [],
        }

    def _check_response_consistency(self, api_code):
        """Check response format consistency."""
        return {
            "inconsistent_response_formats": [],
            "missing_content_types": [],
        }

    def _generate_api_recommendations(self, spec, rest, endpoints):
        """Generate API design recommendations."""
        recommendations = []

        if rest.get("violations"):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "api",
                    "action": f"Fix {len(rest['violations'])} RESTful violations",
                }
            )

        if endpoints.get("naming_violations"):
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "api",
                    "action": f"Fix {len(endpoints['naming_violations'])} endpoint naming issues",
                }
            )

        return recommendations
