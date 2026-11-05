"""Types shared across Phase 1 modules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StyleGuide:
    document_type: str
    purpose: str
    scope: str
    core_topics: list
    optional_topics: list
    tone_and_conventions: str
    section_words: tuple[int, int]


@dataclass(frozen=True)
class PromptTemplate:
    system: str
    user: str
