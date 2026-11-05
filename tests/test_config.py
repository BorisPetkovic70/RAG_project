from pathlib import Path

import pytest
import yaml

from phase1.config import (REQUIRED_PLACEHOLDERS, ConfigError, load_config, load_prompts,
                           load_style_guides, render)

ROOT = Path(__file__).resolve().parent.parent
GUIDES_DIR = ROOT / "style_guides"


def write_config(tmp_path, data):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


@pytest.fixture
def raw_config():
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["config.yaml", "config.smoke.yaml"])
def test_real_configs_load(name):
    cfg = load_config(ROOT / name)
    assert cfg.retry.repair_rounds == 2
    assert cfg.models.section.id == "google/gemma-4-31b-it"
    assert cfg.paths.guides_dir == ROOT / "style_guides"
    assert cfg.toc.leaf_range == (12, 25)


def test_missing_key_names_full_path(tmp_path, raw_config):
    del raw_config["retry"]["repair_rounds"]
    with pytest.raises(ConfigError, match=r"missing config key: retry\.repair_rounds"):
        load_config(write_config(tmp_path, raw_config))


def test_missing_nested_model_key(tmp_path, raw_config):
    del raw_config["models"]["judge"]["providers"]
    with pytest.raises(ConfigError, match=r"missing config key: models\.judge\.providers"):
        load_config(write_config(tmp_path, raw_config))


def test_unknown_key_is_rejected(tmp_path, raw_config):
    raw_config["toc"]["max_dpeth"] = 3
    with pytest.raises(ConfigError, match=r"unknown config key: toc\.max_dpeth"):
        load_config(write_config(tmp_path, raw_config))


def test_too_many_docs_per_tool(tmp_path, raw_config):
    raw_config["generation"]["docs_per_tool"] = 7
    with pytest.raises(ConfigError, match=r"generation\.docs_per_tool"):
        load_config(write_config(tmp_path, raw_config))


def test_too_many_issues_per_doc(tmp_path, raw_config):
    raw_config["generation"]["issues_per_doc"] = [2, 5]
    with pytest.raises(ConfigError, match=r"generation\.issues_per_doc"):
        load_config(write_config(tmp_path, raw_config))


def test_leaf_range_too_small_for_issues(tmp_path, raw_config):
    raw_config["toc"]["leaf_range"] = [3, 25]
    with pytest.raises(ConfigError, match=r"toc\.leaf_range"):
        load_config(write_config(tmp_path, raw_config))


def test_leaf_range_just_large_enough(tmp_path, raw_config):
    raw_config["toc"]["leaf_range"] = [4, 25]
    assert load_config(write_config(tmp_path, raw_config)).toc.leaf_range == (4, 25)


def test_paths_resolve_against_config_dir(tmp_path, raw_config):
    cfg = load_config(write_config(tmp_path, raw_config))
    assert cfg.paths.data_dir == tmp_path / "data"


def copy_guide(tmp_path, doc_type="privacy_policy", edit=None):
    data = yaml.safe_load((GUIDES_DIR / f"{doc_type}.yaml").read_text(encoding="utf-8"))
    if edit:
        edit(data)
    (tmp_path / f"{doc_type}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def test_all_real_guides_load():
    cfg = load_config(ROOT / "config.yaml")
    guides = load_style_guides(cfg.paths.guides_dir, cfg.generation.doc_types)
    assert sorted(guides) == sorted(cfg.generation.doc_types)
    for guide in guides.values():
        low, high = guide.section_words
        assert 0 < low < high


def test_missing_guide_file(tmp_path):
    copy_guide(tmp_path)
    with pytest.raises(ConfigError, match=r"missing style guide: .*terms_of_service\.yaml"):
        load_style_guides(tmp_path, ["privacy_policy", "terms_of_service"])


@pytest.mark.parametrize("field", ["purpose", "core_topics", "tone_and_conventions"])
def test_missing_guide_field(tmp_path, field):
    copy_guide(tmp_path, edit=lambda d: d.pop(field))
    with pytest.raises(ConfigError, match=f"missing field: {field}"):
        load_style_guides(tmp_path, ["privacy_policy"])


def test_missing_section_words(tmp_path):
    copy_guide(tmp_path, edit=lambda d: d["typical_length"].pop("section_words"))
    with pytest.raises(ConfigError, match=r"missing field: typical_length\.section_words"):
        load_style_guides(tmp_path, ["privacy_policy"])


def test_guide_document_type_must_match_file(tmp_path):
    copy_guide(tmp_path, edit=lambda d: d.update(document_type="terms_of_service"))
    with pytest.raises(ConfigError, match="expected 'privacy_policy'"):
        load_style_guides(tmp_path, ["privacy_policy"])


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


def test_complete_prompts_load(tmp_path):
    write_prompts(tmp_path)
    prompts = load_prompts(tmp_path)
    assert sorted(prompts) == sorted(REQUIRED_PLACEHOLDERS)
    assert "$tool_json" in prompts["section"].system


def test_either_placeholder_may_be_in_system(tmp_path):
    move = lambda t: {"system": t["system"] + " $num_tools",
                      "user": t["user"].replace("$num_tools", "")}
    write_prompts(tmp_path, edit=("tool_ideation", move))
    assert "$num_tools" in load_prompts(tmp_path)["tool_ideation"].system


def test_missing_prompt_file(tmp_path):
    write_prompts(tmp_path, skip_step="judge")
    with pytest.raises(ConfigError, match=r"missing prompt file: .*judge\.yaml"):
        load_prompts(tmp_path)


def test_missing_placeholder(tmp_path):
    drop = lambda t: {**t, "user": t["user"].replace("$fix_list", "")}
    write_prompts(tmp_path, edit=("repair", drop))
    with pytest.raises(ConfigError, match=r"repair\.yaml is missing placeholder \$fix_list in user"):
        load_prompts(tmp_path)


def test_placeholder_in_wrong_template(tmp_path):
    move = lambda t: {"system": t["system"].replace("$toc_outline", ""),
                      "user": t["user"] + " $toc_outline"}
    write_prompts(tmp_path, edit=("section", move))
    with pytest.raises(ConfigError, match=r"\$toc_outline in system"):
        load_prompts(tmp_path)


def test_missing_user_text(tmp_path):
    write_prompts(tmp_path, edit=("toc", lambda t: {"system": t["system"]}))
    with pytest.raises(ConfigError, match=r"toc\.yaml is missing text for: user"):
        load_prompts(tmp_path)


def test_render_substitutes_and_raises_on_missing_value():
    assert render("Make $num_tools tools for $$0", {"num_tools": 5}) == "Make 5 tools for $0"
    with pytest.raises(KeyError):
        render("Make $num_tools tools", {})
