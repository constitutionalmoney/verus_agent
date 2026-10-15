"""Read curated public reference material offline, without initializing a daemon.

Content is evidence and integration guidance, not executable instructions or
authorization. Only named, bundled topics can be read; callers cannot supply paths.
"""

from importlib.resources import files
from typing import Any


KNOWLEDGE_AS_OF = "2026-10-15"
KNOWLEDGE_TOPICS = {
    "index": "INDEX.md",
    "mobile": "MOBILE_V1.1.0-21.md",
    "sdk": "SDK_AND_PRIMITIVES.md",
    "dream": "DREAM_APPS.md",
    "resources": "BOOTSTRAP_AND_TREASURY.md",
    "community": "COMMUNITY_PROJECTS.md",
}


def get_knowledge(topic: str = "index") -> dict[str, Any]:
    """Return a dated, source-linked topic from the installed package."""
    if not isinstance(topic, str) or topic not in KNOWLEDGE_TOPICS:
        raise ValueError("Unknown knowledge topic; choose: " + ", ".join(KNOWLEDGE_TOPICS))
    filename = KNOWLEDGE_TOPICS[topic]
    content = files("verus_agent").joinpath("knowledge", filename).read_text(encoding="utf-8")
    return {
        "topic": topic,
        "as_of": KNOWLEDGE_AS_OF,
        "path": "knowledge/" + filename,
        "topics": list(KNOWLEDGE_TOPICS),
        "content": content,
        "authorization": "Reference only; no wallet or blockchain action authorized.",
    }
