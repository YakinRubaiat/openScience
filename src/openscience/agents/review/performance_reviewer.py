"""Performance Review Agent for openScience."""

from openscience.core.agent import BaseAgent, AgentMetadata


class PerformanceReviewerAgent(BaseAgent):
    """
    Agent for reviewing code performance and optimization opportunities.
    
    Reviews:
    - Algorithm complexity
    - Memory usage patterns
    - Database query optimization
    - Caching opportunities
    - Async/await usage
    - Resource leaks
    - Bottlenecks
    """

    metadata = AgentMetadata(
        name="performance_reviewer",
        category="review",
        description="Reviews code performance and identifies optimizations",
        required_skills=["py-spy", "memory-profiler", "line-profiler", "scalene"],
        input_types=["source_code", "runtime_metrics"],
        output_types=["performance_report", "bottlenecks", "recommendations"],
    )

    async def execute(self, task, context):
        """Execute performance review."""
        target_path = task.parameters.get("target_path", "src/")
        runtime_data = task.parameters.get("runtime_data", {})
        
        # Analyze algorithm complexity
        complexity_analysis = self._analyze_complexity(target_path)
        
        # Identify bottlenecks
        bottlenecks = await self.run_skill(
            "py-spy",
            operation="analyze",
            data=runtime_data,
        )
        
        # Check memory usage
        memory_analysis = await self.run_skill(
            "memory-profiler",
            operation="analyze",
            path=target_path,
        )
        
        # Database query analysis
        query_analysis = self._analyze_queries(target_path)
        
        # Async usage review
        async_review = self._review_async_patterns(target_path)
        
        return self.format_result({
            "complexity_analysis": complexity_analysis,
            "bottlenecks": bottlenecks,
            "memory_analysis": memory_analysis,
            "query_analysis": query_analysis,
            "async_review": async_review,
            "recommendations": self._generate_performance_recommendations(
                complexity_analysis,
                bottlenecks,
                memory_analysis,
            ),
        })
    
    def _analyze_complexity(self, target_path):
        """Analyze algorithm complexity."""
        return {
            "high_complexity_functions": [],
            "nested_loops": [],
            "recursive_functions": [],
        }
    
    def _analyze_queries(self, target_path):
        """Analyze database queries."""
        return {
            "n_plus_one_queries": [],
            "missing_indexes": [],
            "inefficient_queries": [],
        }
    
    def _review_async_patterns(self, target_path):
        """Review async/await patterns."""
        return {
            "blocking_calls_in_async": [],
            "missing_async_keywords": [],
            "improper_executor_usage": [],
        }
    
    def _generate_performance_recommendations(self, complexity, bottlenecks, memory):
        """Generate performance recommendations.

        Skill outputs vary by bound tool: ``bottlenecks`` may be a list of
        items, a dict of findings, or empty. Normalize before slicing so a
        ``KeyError: slice(None, 3, None)`` can't escape when a dict is
        passed. Same for ``memory`` which may be a string or list.
        """
        recommendations = []

        bottleneck_items = self._coerce_list(bottlenecks)
        if bottleneck_items:
            recommendations.append({
                "priority": "high",
                "category": "performance",
                "action": f"Optimize {len(bottleneck_items)} identified bottlenecks",
                "top_bottlenecks": bottleneck_items[:3],
            })

        memory_leaks = self._coerce_list(
            memory.get("memory_leaks") if isinstance(memory, dict) else None
        )
        if memory_leaks:
            recommendations.append({
                "priority": "critical",
                "category": "memory",
                "action": "Fix memory leaks",
                "leaks": memory_leaks,
            })

        return recommendations

    @staticmethod
    def _coerce_list(value):
        """Return a list from list / dict / None / str skill outputs.

        Dicts and strings are treated as opaque containers and converted to
        ``[]`` so callers can safely iterate and slice the result.
        """
        if isinstance(value, list):
            return value
        return []
