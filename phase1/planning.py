"""Seeded document-type selection and planted-issue placement."""

import hashlib
from random import Random


def doc_rng(seed, tool_id, doc_type):
    """Return a Random seeded from a stable hash of (seed, tool_id, doc_type).

    Uses sha256 rather than hash(), which is salted per process, so a document
    gets the same draws across runs, resumes and generation orders.
    """
    digest = hashlib.sha256(f"{seed}:{tool_id}:{doc_type}".encode()).digest()
    return Random(int.from_bytes(digest[:8], "big"))


def select_doc_types(num_tools, docs_per_tool, doc_types, rng):
    """Pick docs_per_tool distinct types per tool, keeping type counts balanced.

    Each type gets a quota of total // len(doc_types); the remainder goes as +1
    to types drawn by rng. Each tool takes the types with the most quota left,
    ties broken by a shuffle. Returns {"tool1": [doc_type, ...], ...}.
    """
    base, extra = divmod(num_tools * docs_per_tool, len(doc_types))
    bonus = set(rng.sample(doc_types, extra))
    quota = {t: base + (t in bonus) for t in doc_types}

    selection = {}
    for i in range(1, num_tools + 1):
        candidates = list(doc_types)
        rng.shuffle(candidates)
        candidates.sort(key=lambda t: quota[t], reverse=True)
        chosen = candidates[:docs_per_tool]
        for t in chosen:
            quota[t] -= 1
        selection[f"tool{i}"] = chosen
    return selection


def assign_issues(leaves, issue_types, issues_per_doc, rng):
    """Place k distinct issue types on distinct leaves, k drawn from issues_per_doc.

    A contradiction never goes on the first leaf, since it needs an earlier
    section to contradict. Returns {section_id: issue_type}.
    """
    k = rng.randint(*issues_per_doc)
    types = rng.sample(issue_types, k)
    free = [leaf.id for leaf in leaves]

    assignment = {}
    if "contradiction" in types:
        section_id = rng.choice(free[1:])
        free.remove(section_id)
        assignment[section_id] = "contradiction"
    for issue_type in types:
        if issue_type == "contradiction":
            continue
        section_id = rng.choice(free)
        free.remove(section_id)
        assignment[section_id] = issue_type
    return assignment
