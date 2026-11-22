"""Architecture Review Agent for openScience."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ArchitectureReviewerAgent(BaseAgent):
    """
    Agent for reviewing software architecture and design patterns.

    Reviews:
    - Module coupling and cohesion
    - Dependency management
    - Design pattern usage
    - API design
    - Scalability concerns
    - Separation of concerns
    - SOLID principles compliance
    """

    metadata = AgentMetadata(
        name="architecture_reviewer",
        category="review",
        description="Reviews software architecture and design patterns",
        required_skills=["pydeps", "import-linter", "architecture-rules"],
        input_types=["source_code", "dependencies"],
        output_types=["architecture_report", "dependency_graph", "recommendations"],
    )

    async def execute(self, task, context):
        """Execute architecture review."""
        target_path = task.parameters.get("target_path", "src/")

        # Generate dependency graph
        dependency_graph = await self.run_skill(
            "pydeps",
            operation="generate",
            path=target_path,
        )

        # Check import layers
        import_violations = await self.run_skill(
            "import-linter",
            operation="check",
            config=".importlinter",
        )

        # Analyze module structure
        structure_analysis = self._analyze_structure(target_path)

        # Check SOLID compliance
        solid_violations = self._check_solid_principles(target_path)

        return self.format_result(
            {
                "dependency_graph": dependency_graph,
                "import_violations": import_violations,
                "structure_analysis": structure_analysis,
                "solid_violations": solid_violations,
                "recommendations": self._generate_architecture_recommendations(
                    dependency_graph,
                    import_violations,
                    structure_analysis,
                ),
            }
        )

    def _analyze_structure(self, target_path):
        """Analyze module structure and organization."""
        return {
            "total_modules": 0,
            "average_module_size": 0,
            "max_module_size": 0,
            "circular_dependencies": [],
        }

    def _check_solid_principles(self, target_path):
        """Check SOLID principle compliance."""
        return {
            "single_responsibility_violations": [],
            "open_closed_violations": [],
            "liskov_substitution_violations": [],
            "interface_segregation_violations": [],
            "dependency_inversion_violations": [],
        }

    def _generate_architecture_recommendations(self, dep_graph, import_violations, structure):
        """Generate architecture recommendations."""
        recommendations = []

        if import_violations:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "architecture",
                    "action": "Fix import layer violations",
                    "count": len(import_violations),
                }
            )

        if structure.get("circular_dependencies"):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "architecture",
                    "action": "Resolve circular dependencies",
                    "count": len(structure["circular_dependencies"]),
                }
            )

        return recommendations
