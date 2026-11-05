"""Load and check config.yaml, style guides and prompt templates."""

import dataclasses
import typing
from dataclasses import dataclass
from pathlib import Path
from string import Template

import yaml

from phase1.datatypes import PromptTemplate, StyleGuide


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Paths:
    data_dir: Path
    guides_dir: Path
    prompts_dir: Path
    cache_dir: Path
    log_dir: Path


@dataclass(frozen=True)
class Api:
    base_url: str
    api_key_env: str
    timeout_s: int
    require_parameters: bool
    allow_fallbacks: bool


@dataclass(frozen=True)
class ModelConfig:
    id: str
    reasoning: dict
    providers: tuple[str, ...]


@dataclass(frozen=True)
class Models:
    tool_ideation: ModelConfig
    toc: ModelConfig
    section: ModelConfig
    judge: ModelConfig


@dataclass(frozen=True)
class Temperature:
    tool_ideation: float
    toc_range: tuple[float, float]
    section_range: tuple[float, float]
    judge: float


@dataclass(frozen=True)
class Generation:
    num_tools: int
    docs_per_tool: int
    doc_types: tuple[str, ...]
    issue_types: tuple[str, ...]
    issues_per_doc: tuple[int, int]


@dataclass(frozen=True)
class TocLimits:
    max_depth: int
    leaf_range: tuple[int, int]


@dataclass(frozen=True)
class Validation:
    section_word_tolerance: float


@dataclass(frozen=True)
class Retry:
    max_attempts: int
    repair_rounds: int
    backoff_base_s: float
    max_total_wait_s: float


@dataclass(frozen=True)
class Config:
    seed: int
    paths: Paths
    api: Api
    models: Models
    temperature: Temperature
    generation: Generation
    toc: TocLimits
    validation: Validation
    retry: Retry


def _build(cls, data, prefix, base_dir):
    """Build dataclass `cls` from a dict, failing on missing or unknown keys."""
    where = prefix.rstrip(".") or "top level"
    if not isinstance(data, dict):
        raise ConfigError(f"config section {where} must be a mapping")

    hints = typing.get_type_hints(cls)
    names = [f.name for f in dataclasses.fields(cls)]
    for key in data:
        if key not in names:
            raise ConfigError(f"unknown config key: {prefix}{key}")

    values = {}
    for name in names:
        key_path = prefix + name
        if name not in data:
            raise ConfigError(f"missing config key: {key_path}")
        hint, value = hints[name], data[name]
        if dataclasses.is_dataclass(hint):
            value = _build(hint, value, key_path + ".", base_dir)
        elif hint is Path:
            value = base_dir / value
        elif typing.get_origin(hint) is tuple:
            value = tuple(value)
        values[name] = value
    return cls(**values)


def _check_ranges(cfg):
    gen = cfg.generation
    if gen.docs_per_tool > len(gen.doc_types):
        raise ConfigError(
            f"generation.docs_per_tool ({gen.docs_per_tool}) exceeds the "
            f"{len(gen.doc_types)} entries in generation.doc_types")
    max_issues = gen.issues_per_doc[1]
    if max_issues > len(gen.issue_types):
        raise ConfigError(
            f"generation.issues_per_doc max ({max_issues}) exceeds the "
            f"{len(gen.issue_types)} entries in generation.issue_types")
    if min(cfg.toc.leaf_range) < max_issues + 1:
        raise ConfigError(
            f"toc.leaf_range min ({min(cfg.toc.leaf_range)}) must be at least "
            f"generation.issues_per_doc max + 1 ({max_issues + 1})")


def load_config(path) -> Config:
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    cfg = _build(Config, data, "", path.parent)
    _check_ranges(cfg)
    return cfg


GUIDE_FIELDS = ["document_type", "purpose", "scope", "core_topics",
                "optional_topics", "tone_and_conventions"]


def load_style_guides(guides_dir, doc_types) -> dict[str, StyleGuide]:
    guides = {}
    for doc_type in doc_types:
        path = Path(guides_dir) / f"{doc_type}.yaml"
        if not path.exists():
            raise ConfigError(f"missing style guide: {path}")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for field in GUIDE_FIELDS:
            if field not in data:
                raise ConfigError(f"style guide {path} is missing field: {field}")
        if "section_words" not in (data.get("typical_length") or {}):
            raise ConfigError(
                f"style guide {path} is missing field: typical_length.section_words")
        if data["document_type"] != doc_type:
            raise ConfigError(
                f"style guide {path} has document_type {data['document_type']!r}, "
                f"expected {doc_type!r}")

        guides[doc_type] = StyleGuide(
            **{field: data[field] for field in GUIDE_FIELDS},
            section_words=tuple(data["typical_length"]["section_words"]))
    return guides


# Placeholders each step's templates must contain. "either" means the step is
# rendered as one {system, user} pair, so each name may sit in either template.
REQUIRED_PLACEHOLDERS = {
    "tool_ideation": {"either": ["num_tools"]},
    "toc": {"either": ["tool_json", "doc_type", "purpose", "scope", "core_topics",
                       "optional_topics", "tone_and_conventions", "max_depth",
                       "leaf_range"]},
    "section": {
        "system": ["tool_json", "doc_type", "tone_and_conventions", "toc_outline",
                   "sections_so_far"],
        "user": ["number", "title", "description", "section_words", "html_contract",
                 "issue_instruction"],
    },
    "repair": {
        "system": ["tool_json", "doc_type", "tone_and_conventions", "full_document"],
        "user": ["number", "title", "description", "section_words", "html_contract",
                 "issue_instruction", "fix_list"],
    },
    "judge": {"either": ["tool_json", "doc_type", "html", "planted",
                         "issue_type_definitions"]},
}


def load_prompts(prompts_dir) -> dict[str, PromptTemplate]:
    prompts = {}
    for step, required in REQUIRED_PLACEHOLDERS.items():
        path = Path(prompts_dir) / f"{step}.yaml"
        if not path.exists():
            raise ConfigError(f"missing prompt file: {path}")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for part in ("system", "user"):
            if not isinstance(data.get(part), str):
                raise ConfigError(f"prompt file {path} is missing text for: {part}")

        found = {part: set(Template(data[part]).get_identifiers())
                 for part in ("system", "user")}
        found["either"] = found["system"] | found["user"]
        for part, names in required.items():
            for name in names:
                if name not in found[part]:
                    raise ConfigError(
                        f"prompt file {path} is missing placeholder ${name} in {part}")

        prompts[step] = PromptTemplate(system=data["system"], user=data["user"])
    return prompts


def render(template: str, values: dict) -> str:
    return Template(template).substitute(values)
