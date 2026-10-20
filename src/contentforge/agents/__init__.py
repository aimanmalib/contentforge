"""ContentForge Agents — 8 specialized AI agents for content pipeline."""

from .base import AgentResult, BaseAgent
from .editor import EditorAgent
from .outline import OutlineAgent
from .publisher import PublisherAgent
from .quality import QualityAgent
from .research import ResearchAgent
from .seo import SEOAgent
from .translator import TranslatorAgent
from .writer import WriterAgent

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "research": ResearchAgent,
    "outline": OutlineAgent,
    "writer": WriterAgent,
    "seo": SEOAgent,
    "editor": EditorAgent,
    "translator": TranslatorAgent,
    "quality": QualityAgent,
    "publisher": PublisherAgent,
}


def get_agent(name: str, **kwargs) -> BaseAgent:
    cls = AGENT_REGISTRY.get(name)
    if not cls:
        raise ValueError(f"Unknown agent: {name}. Available: {list(AGENT_REGISTRY)}")
    return cls(**kwargs)


__all__ = [
    "BaseAgent",
    "AgentResult",
    "AGENT_REGISTRY",
    "get_agent",
    "ResearchAgent",
    "OutlineAgent",
    "WriterAgent",
    "SEOAgent",
    "EditorAgent",
    "TranslatorAgent",
    "QualityAgent",
    "PublisherAgent",
]
