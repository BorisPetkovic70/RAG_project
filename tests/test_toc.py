import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from phase1.config import load_config
from phase1.toc import build_toc_tree, flatten_tree, load_toc, save_toc, validate_toc

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "toc_entries.json"
TOOL = SimpleNamespace(name="Lumora Scribe")


@pytest.fixture(scope="module", params=["config.yaml", "config.smoke.yaml"])
def cfg(request):
    return load_config(ROOT / request.param)


@pytest.fixture
def entries():
    return json.loads(FIXTURE.read_text())


def entry(id, parent_id=None):
    return {"id": id, "parent_id": parent_id, "title": f"Title {id}", "description": f"About {id}"}


def flat_toc(leaves, depth=1):
    """One chain `depth` entries deep (its bottom is a leaf), plus top-level leaves up to `leaves`."""
    chain = [entry("c1")] + [entry(f"c{d}", f"c{d - 1}") for d in range(2, depth + 1)]
    return chain + [entry(f"leaf{i}") for i in range(leaves - 1)]


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)


# build_toc_tree

def test_build_numbers_top_level_entries_in_list_order(entries):
    tree = build_toc_tree(entries)
    assert [(n.number, n.title) for n in tree] == [
        ("1", "Introduction"),
        ("2", "Information We Collect"),
        ("3", "How We Use Information"),
        ("4", "Sharing of Information"),
        ("5", "Data Retention"),
        ("6", "Your Rights"),
        ("7", "Contact Us"),
    ]


def test_build_computes_number_level_and_id_down_to_depth_four(entries):
    collect = build_toc_tree(entries)[1]
    payment = collect.children[0].children[1]
    card = payment.children[0]
    assert (payment.id, payment.number, payment.level) == ("s2-1-2", "2.1.2", 3)
    assert (card.id, card.number, card.level, card.title) == ("s2-1-2-1", "2.1.2.1", 4, "Card Data")


def test_build_replaces_llm_ids_with_position_ids(entries):
    ids = [n.id for n in walk(build_toc_tree(entries))]
    assert "intro" not in ids
    assert ids[:4] == ["s1", "s2", "s2-1", "s2-1-1"]


def test_build_marks_only_childless_nodes_as_leaves(entries):
    nodes = list(walk(build_toc_tree(entries)))
    assert all(n.is_leaf == (n.children == ()) for n in nodes)
    assert sum(n.is_leaf for n in nodes) == 13


def test_build_keeps_title_and_description(entries):
    intro = build_toc_tree(entries)[0]
    assert intro.title == "Introduction"
    assert intro.description == "Who we are and what this policy covers."


def test_build_orders_siblings_by_list_position_not_by_parent_position():
    tree = build_toc_tree([entry("a"), entry("b"), entry("a2", "a"), entry("a1", "a")])
    assert [(n.number, n.title) for n in tree[0].children] == [("1.1", "Title a2"), ("1.2", "Title a1")]
    assert tree[1].number == "2"


def test_build_single_entry_is_one_leaf():
    (node,) = build_toc_tree([entry("only")])
    assert (node.id, node.number, node.level, node.is_leaf) == ("s1", "1", 1, True)


def test_build_same_entries_give_same_tree(entries):
    assert build_toc_tree(entries) == build_toc_tree(json.loads(FIXTURE.read_text()))


# flatten_tree

def test_flatten_returns_nodes_in_document_order(entries):
    numbers = [n.number for n in flatten_tree(build_toc_tree(entries))]
    assert numbers == [
        "1", "2", "2.1", "2.1.1", "2.1.2", "2.1.2.1", "2.1.2.2", "2.2",
        "3", "3.1", "3.2", "4", "4.1", "4.2", "5", "6", "6.1", "6.2", "7",
    ]


def test_flatten_includes_every_entry_once(entries):
    nodes = flatten_tree(build_toc_tree(entries))
    assert len(nodes) == len(entries)
    assert len({n.id for n in nodes}) == len(entries)


def test_flatten_leaves_keep_document_order(entries):
    leaves = [n.title for n in flatten_tree(build_toc_tree(entries)) if n.is_leaf]
    assert leaves[:4] == ["Introduction", "Account Information", "Card Data", "Billing Address"]
    assert leaves[-1] == "Contact Us"


def test_flatten_returns_the_tree_nodes_themselves(entries):
    tree = build_toc_tree(entries)
    assert flatten_tree(tree)[1] is tree[1]


def test_flatten_empty_tree_is_empty():
    assert flatten_tree([]) == []


# validate_toc

def test_validate_accepts_fixture_toc(entries, cfg):
    assert validate_toc(entries, cfg) == []


def test_validate_reports_duplicate_id(entries, cfg):
    entries[4]["id"] = "account"
    assert "duplicate id: account" in validate_toc(entries, cfg)


def test_validate_reports_unknown_parent(entries, cfg):
    entries[3]["parent_id"] = "missing"
    assert validate_toc(entries, cfg) == ["account: unknown parent_id missing"]


def test_validate_reports_child_before_parent(entries, cfg):
    entries[2], entries[3] = entries[3], entries[2]
    assert validate_toc(entries, cfg) == ["account: appears before its parent provided"]


@pytest.mark.parametrize("field", ["title", "description"])
@pytest.mark.parametrize("value", ["", "   "])
def test_validate_reports_empty_text(entries, cfg, field, value):
    entries[0][field] = value
    assert validate_toc(entries, cfg) == [f"intro: empty {field}"]


def test_validate_reports_cycle(cfg):
    toc = flat_toc(12) + [entry("x", "y"), entry("y", "x")]
    errors = validate_toc(toc, cfg)
    assert "x: parent chain has a cycle" in errors
    assert "y: parent chain has a cycle" in errors


def test_validate_reports_entry_that_is_its_own_parent(cfg):
    toc = flat_toc(12) + [entry("self", "self")]
    assert "self: parent chain has a cycle" in validate_toc(toc, cfg)


def test_validate_accepts_depth_at_max_depth(cfg):
    assert validate_toc(flat_toc(12, depth=cfg.toc.max_depth), cfg) == []


def test_validate_reports_depth_past_max_depth(cfg):
    depth = cfg.toc.max_depth + 1
    assert validate_toc(flat_toc(12, depth=depth), cfg) == [
        f"c{depth}: depth {depth} exceeds max_depth {cfg.toc.max_depth}"
    ]


@pytest.mark.parametrize("bound", [0, 1])
def test_validate_accepts_leaf_count_at_range_limits(cfg, bound):
    assert validate_toc(flat_toc(cfg.toc.leaf_range[bound]), cfg) == []


@pytest.mark.parametrize("bound, step", [(0, -1), (1, 1)])
def test_validate_reports_leaf_count_outside_range(cfg, bound, step):
    count = cfg.toc.leaf_range[bound] + step
    low, high = cfg.toc.leaf_range
    assert validate_toc(flat_toc(count), cfg) == [f"leaf count {count} outside leaf_range [{low}, {high}]"]


def test_validate_counts_only_childless_entries_as_leaves(cfg):
    toc = flat_toc(cfg.toc.leaf_range[0], depth=3)
    assert validate_toc(toc, cfg) == []
    assert len(toc) == cfg.toc.leaf_range[0] + 2


def test_validate_reports_empty_toc(cfg):
    low, high = cfg.toc.leaf_range
    assert validate_toc([], cfg) == [f"leaf count 0 outside leaf_range [{low}, {high}]"]


# save_toc / load_toc

def test_save_then_load_gives_the_same_tree(entries, tmp_path):
    tree = build_toc_tree(entries)
    path = tmp_path / "toc_privacy_policy.json"
    save_toc(path, TOOL, "privacy_policy", tree)
    assert load_toc(path) == tree


def test_saved_toc_is_a_nested_json_object_in_design_format(entries, tmp_path):
    """Design §5: TOC file is a real nested JSON object, not a string."""
    path = tmp_path / "toc_privacy_policy.json"
    save_toc(path, TOOL, "privacy_policy", build_toc_tree(entries))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert (data["tool"], data["document_type"]) == ("Lumora Scribe", "privacy_policy")
    card = data["sections"][1]["children"][0]["children"][1]["children"][0]
    assert card == {
        "id": "s2-1-2-1", "number": "2.1.2.1", "level": 4, "title": "Card Data",
        "description": "How card details are handled by the payment processor.", "children": [],
    }


def test_saved_toc_has_no_issue_or_leaf_fields(entries, tmp_path):
    """Design §5: no issue information in the TOC; is_leaf is derived on load."""
    path = tmp_path / "toc.json"
    save_toc(path, TOOL, "privacy_policy", build_toc_tree(entries))
    keys = {k for node in json.loads(path.read_text())["sections"] for k in node}
    assert keys == {"id", "number", "level", "title", "description", "children"}


def test_save_keeps_non_ascii_text(tmp_path):
    tree = build_toc_tree([{"id": "a", "parent_id": None, "title": "Données personnelles", "description": "Überblick"}])
    path = tmp_path / "toc.json"
    save_toc(path, TOOL, "privacy_policy", tree)
    assert "Données personnelles" in path.read_text(encoding="utf-8")
    assert load_toc(path) == tree


def test_load_derives_leaves_from_children(entries, tmp_path):
    path = tmp_path / "toc.json"
    save_toc(path, TOOL, "privacy_policy", build_toc_tree(entries))
    nodes = flatten_tree(load_toc(path))
    assert sum(n.is_leaf for n in nodes) == 13
    assert all(n.is_leaf == (n.children == ()) for n in nodes)
