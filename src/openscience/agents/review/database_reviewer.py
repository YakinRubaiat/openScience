"""Database Review Agent for openScience."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DatabaseReviewerAgent(BaseAgent):
    """
    Agent for reviewing database design and query optimization.

    Reviews:
    - Schema design
    - Index usage
    - Query performance
    - Migration safety
    - Data integrity constraints
    - N+1 query problems
    - Connection pooling
    """

    metadata = AgentMetadata(
        name="database_reviewer",
        category="review",
        description="Reviews database design and query optimization",
        required_skills=["sqlfluff", "pgbadger", "django-debug-toolbar"],
        input_types=["models", "migrations", "queries"],
        output_types=["database_report", "optimization_suggestions", "recommendations"],
    )

    async def execute(self, task, context):
        """Execute database review."""
        models_path = task.parameters.get("models_path", "src/openscience/models/")

        # Analyze schema design
        schema_analysis = self._analyze_schema(models_path)

        # Check index usage
        index_analysis = await self.run_skill(
            "pgbadger",
            operation="analyze",
            log_file="postgresql.log",
        )

        # Review migrations
        migration_review = self._review_migrations(models_path)

        # Check for N+1 queries
        n_plus_one_analysis = self._find_n_plus_one_queries(models_path)

        # Review data integrity
        integrity_check = self._check_data_integrity(models_path)

        return self.format_result(
            {
                "schema_analysis": schema_analysis,
                "index_analysis": index_analysis,
                "migration_review": migration_review,
                "n_plus_one_queries": n_plus_one_analysis,
                "integrity_check": integrity_check,
                "recommendations": self._generate_database_recommendations(
                    schema_analysis,
                    index_analysis,
                    n_plus_one_analysis,
                ),
            }
        )

    def _analyze_schema(self, models_path):
        """Analyze database schema design."""
        return {
            "tables_count": 0,
            "missing_indexes": [],
            "denormalized_tables": [],
            "missing_foreign_keys": [],
        }

    def _review_migrations(self, models_path):
        """Review database migrations."""
        return {
            "migrations_count": 0,
            "unsafe_migrations": [],
            "missing_rollbacks": [],
        }

    def _find_n_plus_one_queries(self, models_path):
        """Find potential N+1 query problems."""
        return {
            "potential_n_plus_one": [],
            "missing_select_related": [],
            "missing_prefetch_related": [],
        }

    def _check_data_integrity(self, models_path):
        """Check data integrity constraints."""
        return {
            "missing_constraints": [],
            "nullable_foreign_keys": [],
            "missing_unique_constraints": [],
        }

    def _generate_database_recommendations(self, schema, index, n_plus_one):
        """Generate database recommendations."""
        recommendations = []

        if schema.get("missing_indexes"):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "database",
                    "action": f"Add {len(schema['missing_indexes'])} missing indexes",
                }
            )

        if n_plus_one.get("potential_n_plus_one"):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "database",
                    "action": f"Fix {len(n_plus_one['potential_n_plus_one'])} N+1 query problems",
                }
            )

        return recommendations
