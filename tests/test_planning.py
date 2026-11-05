from collections import Counter
from pathlib import Path
from random import Random
from types import SimpleNamespace

import pytest

from phase1.config import load_config
from phase1.planning import assign_issues, doc_rng, select_doc_types

ROOT = Path(__file__).resolve().parent.parent
SEEDS = range(500)


@pytest.fixture(scope="module")
def cfg():
    return load_config(ROOT / "config.yaml")


@pytest.fixture(scope="module")
def gen(cfg):
    return cfg.generation


def draws(rng, n=5):
    return [rng.randint(0, 2**31 - 1) for _ in range(n)]


def make_leaves(n):
    return [SimpleNamespace(id=f"s{i}") for i in range(1, n + 1)]


def type_counts(selection):
    return Counter(t for types in selection.values() for t in types)


# doc_rng

def test_doc_rng_same_inputs_give_same_draws():
    assert draws(doc_rng(42, "tool1", "privacy_policy")) == draws(doc_rng(42, "tool1", "privacy_policy"))


def test_doc_rng_draws_are_pinned_across_processes():
    """Design §Planning: stable hash, so draws don't change between runs (unlike salted hash())."""
    assert doc_rng(42, "tool1", "privacy_policy").randint(0, 2**31 - 1) == 675990160


def test_doc_rng_does_not_depend_on_call_order():
    a_first = draws(doc_rng(42, "tool1", "privacy_policy"))
    b_after = draws(doc_rng(42, "tool2", "terms_of_service"))
    b_first = draws(doc_rng(42, "tool2", "terms_of_service"))
    a_after = draws(doc_rng(42, "tool1", "privacy_policy"))
    assert (a_first, b_after) == (a_after, b_first)


def test_doc_rng_differs_by_seed_tool_and_doc_type():
    base = draws(doc_rng(42, "tool1", "privacy_policy"))
    assert draws(doc_rng(43, "tool1", "privacy_policy")) != base
    assert draws(doc_rng(42, "tool2", "privacy_policy")) != base
    assert draws(doc_rng(42, "tool1", "terms_of_service")) != base


# select_doc_types

def test_full_run_quotas_are_3_3_3_3_4_4(gen):
    for seed in SEEDS:
        selection = select_doc_types(gen.num_tools, gen.docs_per_tool, gen.doc_types, Random(seed))
        counts = type_counts(selection)
        assert set(counts) == set(gen.doc_types)
        assert sorted(counts.values()) == [3, 3, 3, 3, 4, 4]


def test_each_tool_gets_docs_per_tool_distinct_types(gen):
    for seed in SEEDS:
        selection = select_doc_types(gen.num_tools, gen.docs_per_tool, gen.doc_types, Random(seed))
        assert list(selection) == [f"tool{i}" for i in range(1, gen.num_tools + 1)]
        for types in selection.values():
            assert len(set(types)) == gen.docs_per_tool


def test_smoke_config_selects_distinct_types_per_tool():
    smoke = load_config(ROOT / "config.smoke.yaml").generation
    selection = select_doc_types(smoke.num_tools, smoke.docs_per_tool, smoke.doc_types, Random(42))
    assert list(selection) == [f"tool{i}" for i in range(1, smoke.num_tools + 1)]
    assert all(len(set(types)) == smoke.docs_per_tool for types in selection.values())
    assert max(type_counts(selection).values()) == 1


@pytest.mark.parametrize("num_tools, docs_per_tool", [(1, 1), (4, 3), (7, 5)])
def test_quotas_stay_balanced_for_other_run_sizes(gen, num_tools, docs_per_tool):
    for seed in SEEDS:
        selection = select_doc_types(num_tools, docs_per_tool, gen.doc_types, Random(seed))
        counts = type_counts(selection)
        assert sum(counts.values()) == num_tools * docs_per_tool
        assert max(counts.values()) - min(counts.get(t, 0) for t in gen.doc_types) <= 1
        assert all(len(set(types)) == docs_per_tool for types in selection.values())


def test_docs_per_tool_at_limit_gives_every_tool_every_type(gen):
    """Design §Planning: docs_per_tool <= len(doc_types); one past is rejected in test_config::test_value_range_limits."""
    limit = len(gen.doc_types)
    for seed in SEEDS:
        selection = select_doc_types(gen.num_tools, limit, gen.doc_types, Random(seed))
        assert all(set(types) == set(gen.doc_types) for types in selection.values())


def test_select_doc_types_same_seed_gives_same_selection(gen):
    args = (gen.num_tools, gen.docs_per_tool, gen.doc_types)
    assert select_doc_types(*args, Random(42)) == select_doc_types(*args, Random(42))


def test_select_doc_types_varies_with_seed(gen):
    args = (gen.num_tools, gen.docs_per_tool, gen.doc_types)
    results = {str(select_doc_types(*args, Random(seed))) for seed in range(20)}
    assert len(results) > 1


# assign_issues

def test_issue_count_and_types_stay_within_config(cfg, gen):
    leaves = make_leaves(cfg.toc.leaf_range[0])
    leaf_ids = {leaf.id for leaf in leaves}
    counts = set()
    for seed in SEEDS:
        assignment = assign_issues(leaves, gen.issue_types, gen.issues_per_doc, Random(seed))
        counts.add(len(assignment))
        assert set(assignment.values()) <= set(gen.issue_types)
        assert len(set(assignment.values())) == len(assignment)
        assert set(assignment) <= leaf_ids
    assert counts == set(range(gen.issues_per_doc[0], gen.issues_per_doc[1] + 1))


def test_contradiction_never_lands_on_first_leaf(cfg, gen):
    leaves = make_leaves(cfg.toc.leaf_range[0])
    contradictions = 0
    for seed in SEEDS:
        assignment = assign_issues(leaves, gen.issue_types, gen.issues_per_doc, Random(seed))
        assert assignment.get(leaves[0].id) != "contradiction"
        contradictions += "contradiction" in assignment.values()
    assert contradictions > 0


def test_issues_fit_on_leaf_range_min_at_limit(gen):
    """Design §Planning: min(leaf_range) >= issues_per_doc max + 1; one past is rejected in test_config::test_value_range_limits."""
    max_issues = gen.issues_per_doc[1]
    leaves = make_leaves(max_issues + 1)
    for seed in SEEDS:
        assignment = assign_issues(leaves, gen.issue_types, (max_issues, max_issues), Random(seed))
        assert len(assignment) == max_issues
        assert assignment.get(leaves[0].id) != "contradiction"


def test_issues_per_doc_max_at_limit_uses_every_issue_type(gen):
    """Design §Planning: issues_per_doc max <= len(issue_types); one past is rejected in test_config::test_value_range_limits."""
    limit = len(gen.issue_types)
    leaves = make_leaves(limit + 1)
    for seed in SEEDS:
        assignment = assign_issues(leaves, gen.issue_types, (limit, limit), Random(seed))
        assert sorted(assignment.values()) == sorted(gen.issue_types)
        assert assignment.get(leaves[0].id) != "contradiction"


def test_assign_issues_same_seed_gives_same_assignment(cfg, gen):
    args = (make_leaves(cfg.toc.leaf_range[1]), gen.issue_types, gen.issues_per_doc)
    assert assign_issues(*args, Random(7)) == assign_issues(*args, Random(7))
