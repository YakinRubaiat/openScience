"""General skills: skill registry binding skill names to real implementations."""

from openscience.skills.general import llm_summarization, pubmed_api, topic_modeling

SKILL_REGISTRY = {
    "pubmed_api": pubmed_api,
    "llm_summarization": llm_summarization,
    "topic_modeling": topic_modeling,
}


def run_skill(skill_name: str, operation: str, **kwargs):
    """Dispatch a skill call to its real implementation."""
    if skill_name not in SKILL_REGISTRY:
        raise ValueError(f"Unknown skill: {skill_name}")
    module = SKILL_REGISTRY[skill_name]
    return module.run(operation=operation, **kwargs)
