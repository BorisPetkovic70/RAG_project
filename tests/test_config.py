from pathlib import Path

import pytest
import yaml

from phase1.config import (GUIDE_FIELDS, REQUIRED_PLACEHOLDERS, ConfigError, load_config,
                           load_prompts, load_style_guides, render)

ROOT = Path(__file__).resolve().parent.parent
GUIDES_DIR = ROOT / "style_guides"


def write_config(tmp_path, data):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


@pytest.fixture
def raw_config():
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


# load_config

@pytest.mark.parametrize("name", ["config.yaml", "config.smoke.yaml"])
def test_loads_real_configs(name):
    cfg = load_config(ROOT / name)
    assert cfg.retry.repair_rounds == 2
    assert cfg.models.section.id == "google/gemma-4-31b-it"
    assert cfg.models.judge.providers == ("deepinfra/fp8", "inference-net/fp8", "nebius/fp8")
    assert cfg.paths.guides_dir == ROOT / "style_guides"
    assert cfg.toc.leaf_range == (12, 25)


@pytest.mark.parametrize("key_path", [
    "seed",
    "retry",
    "retry.repair_rounds",
    "paths.prompts_dir",
    "models.judge.providers",
])
def test_rejects_missing_key_naming_full_path(tmp_path, raw_config, key_path):
    *parents, last = key_path.split(".")
    section = raw_config
    for part in parents:
        section = section[part]
    del section[last]
    with pytest.raises(ConfigError, match=rf"missing config key: {key_path}$"):
        load_config(write_config(tmp_path, raw_config))


def test_rejects_unknown_key(tmp_path, raw_config):
    """D50: unknown config keys are rejected."""
    raw_config["toc"]["max_dpeth"] = 3
    with pytest.raises(ConfigError, match=r"unknown config key: toc\.max_dpeth"):
        load_config(write_config(tmp_path, raw_config))


def test_rejects_section_that_is_not_a_mapping(tmp_path, raw_config):
    raw_config["retry"] = 5
    with pytest.raises(ConfigError, match=r"config section retry must be a mapping"):
        load_config(write_config(tmp_path, raw_config))


@pytest.mark.parametrize("section, key, at_limit, past_limit", [
    ("generation", "docs_per_tool", 6, 7),         # 6 doc types
    ("generation", "issues_per_doc", [2, 4], [2, 5]),  # 4 issue types
    ("toc", "leaf_range", [4, 25], [3, 25]),       # issues_per_doc max 3, plus one leaf
])
def test_value_range_limits(tmp_path, raw_config, section, key, at_limit, past_limit):
    raw_config[section][key] = at_limit
    load_config(write_config(tmp_path, raw_config))

    raw_config[section][key] = past_limit
    with pytest.raises(ConfigError, match=rf"{section}\.{key}"):
        load_config(write_config(tmp_path, raw_config))


def test_resolves_paths_against_config_folder(tmp_path, raw_config):
    """D51: relative paths resolve against the config file's folder."""
    cfg = load_config(write_config(tmp_path, raw_config))
    assert cfg.paths.data_dir == tmp_path / "data"
    assert cfg.paths.cache_dir == tmp_path / ".cache"


# load_style_guides

def copy_guide(tmp_path, doc_type="privacy_policy", edit=None):
    data = yaml.safe_load((GUIDES_DIR / f"{doc_type}.yaml").read_text(encoding="utf-8"))
    if edit:
        edit(data)
    (tmp_path / f"{doc_type}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def test_loads_all_real_guides():
    cfg = load_config(ROOT / "config.yaml")
    guides = load_style_guides(cfg.paths.guides_dir, cfg.generation.doc_types)
    assert sorted(guides) == sorted(cfg.generation.doc_types)
    for doc_type, guide in guides.items():
        assert guide.document_type == doc_type
        low, high = guide.section_words
        assert 0 < low < high


def test_rejects_missing_guide_file(tmp_path):
    copy_guide(tmp_path)
    with pytest.raises(ConfigError, match=r"missing style guide: .*terms_of_service\.yaml"):
        load_style_guides(tmp_path, ["privacy_policy", "terms_of_service"])


@pytest.mark.parametrize("field", GUIDE_FIELDS)
def test_rejects_guide_missing_field(tmp_path, field):
    copy_guide(tmp_path, edit=lambda d: d.pop(field))
    with pytest.raises(ConfigError, match=rf"privacy_policy\.yaml is missing field: {field}$"):
        load_style_guides(tmp_path, ["privacy_policy"])


@pytest.mark.parametrize("edit", [
    lambda d: d["typical_length"].pop("section_words"),
    lambda d: d.pop("typical_length"),
], ids=["no_section_words", "no_typical_length"])
def test_rejects_guide_missing_section_words(tmp_path, edit):
    copy_guide(tmp_path, edit=edit)
    with pytest.raises(ConfigError, match=r"missing field: typical_length\.section_words"):
        load_style_guides(tmp_path, ["privacy_policy"])


def test_rejects_guide_with_wrong_document_type(tmp_path):
    """D50: a guide's document_type must match its file name."""
    copy_guide(tmp_path, edit=lambda d: d.update(document_type="terms_of_service"))
    with pytest.raises(ConfigError, match="expected 'privacy_policy'"):
        load_style_guides(tmp_path, ["privacy_policy"])


# load_prompts

def write_prompts(prompts_dir, skip_step=None, edit=None):
    """Write a complete set of prompt files built from REQUIRED_PLACEHOLDERS."""
    for step, required in REQUIRED_PLACEHOLDERS.items():
        if step == skip_step:
            continue
        texts = {"system": "System text for " + step, "user": "User text, costs $$5."}
        for part, names in required.items():
            target = "user" if part == "either" else part
            texts[target] += "\n" + "\n".join(f"{n}: ${n}" for n in names)
        if edit and step == edit[0]:
            texts = edit[1](texts)
        (prompts_dir / f"{step}.yaml").write_text(yaml.safe_dump(texts), encoding="utf-8")


def test_loads_complete_prompts(tmp_path):
    write_prompts(tmp_path)
    prompts = load_prompts(tmp_path)
    assert sorted(prompts) == sorted(REQUIRED_PLACEHOLDERS)
    assert "$tool_json" in prompts["section"].system
    assert "$fix_list" in prompts["repair"].user


def test_accepts_single_render_placeholder_in_system(tmp_path):
    """D48: single-render steps accept each placeholder in either template."""
    move = lambda t: {"system": t["system"] + " $num_tools",
                      "user": t["user"].replace("$num_tools", "")}
    write_prompts(tmp_path, edit=("tool_ideation", move))
    assert "$num_tools" in load_prompts(tmp_path)["tool_ideation"].system


def test_rejects_missing_prompt_file(tmp_path):
    write_prompts(tmp_path, skip_step="judge")
    with pytest.raises(ConfigError, match=r"missing prompt file: .*judge\.yaml"):
        load_prompts(tmp_path)


@pytest.mark.parametrize("step, part, name", [
    ("tool_ideation", "user", "num_tools"),
    ("toc", "user", "leaf_range"),
    ("judge", "user", "issue_type_definitions"),
    ("section", "system", "sections_so_far"),
    ("repair", "user", "fix_list"),
])
def test_rejects_prompt_missing_placeholder(tmp_path, step, part, name):
    drop = lambda t: {**t, part: t[part].replace(f"${name}", "")}
    write_prompts(tmp_path, edit=(step, drop))
    expected_part = "either" if "either" in REQUIRED_PLACEHOLDERS[step] else part
    with pytest.raises(ConfigError,
                       match=rf"{step}\.yaml is missing placeholder \${name} in {expected_part}"):
        load_prompts(tmp_path)


def test_rejects_per_template_placeholder_in_wrong_template(tmp_path):
    """D48: section and repair placeholders are checked per template."""
    move = lambda t: {"system": t["system"].replace("$toc_outline", ""),
                      "user": t["user"] + " $toc_outline"}
    write_prompts(tmp_path, edit=("section", move))
    with pytest.raises(ConfigError, match=r"\$toc_outline in system"):
        load_prompts(tmp_path)


@pytest.mark.parametrize("part", ["system", "user"])
def test_rejects_prompt_missing_text(tmp_path, part):
    write_prompts(tmp_path, edit=("toc", lambda t: {k: v for k, v in t.items() if k != part}))
    with pytest.raises(ConfigError, match=rf"toc\.yaml is missing text for: {part}"):
        load_prompts(tmp_path)


# render

def test_render_fills_placeholders_and_unescapes_dollar():
    assert render("Make $num_tools tools for $$0", {"num_tools": 5}) == "Make 5 tools for $0"


def test_render_raises_on_missing_value():
    with pytest.raises(KeyError, match="num_tools"):
        render("Make $num_tools tools", {})
