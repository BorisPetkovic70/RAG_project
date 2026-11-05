"""Validate the flat LLM TOC, build the nested tree, and save/load it."""

import json

from phase1.datatypes import TocNode


def validate_toc(entries, cfg):
    """Return the problems in a flat TOC as messages naming the entry; empty means valid.

    Checks unique ids, known parents, no cycles, parents before children,
    non-empty title and description, depth <= toc.max_depth and the leaf
    count within toc.leaf_range.
    """
    errors = []
    parents = {}
    for entry in entries:
        if entry["id"] in parents:
            errors.append(f"duplicate id: {entry['id']}")
        parents[entry["id"]] = entry["parent_id"]

    seen = set()
    for entry in entries:
        entry_id, parent_id = entry["id"], entry["parent_id"]
        for field in ("title", "description"):
            if not entry[field].strip():
                errors.append(f"{entry_id}: empty {field}")
        if parent_id is not None and parent_id in parents and parent_id not in seen:
            errors.append(f"{entry_id}: appears before its parent {parent_id}")
        seen.add(entry_id)
        errors.extend(_chain_errors(entry_id, parents, cfg.toc.max_depth))

    used_as_parent = set(parents.values())
    leaf_count = sum(entry["id"] not in used_as_parent for entry in entries)
    low, high = cfg.toc.leaf_range
    if not low <= leaf_count <= high:
        errors.append(f"leaf count {leaf_count} outside leaf_range [{low}, {high}]")
    return errors


def _chain_errors(entry_id, parents, max_depth):
    """Walk from entry_id up to the root; report an unknown parent, a cycle or too much depth."""
    chain = [entry_id]
    while (parent_id := parents[chain[-1]]) is not None:
        if parent_id not in parents:
            return [f"{chain[-1]}: unknown parent_id {parent_id}"] if len(chain) == 1 else []
        if parent_id in chain:
            return [f"{entry_id}: parent chain has a cycle"]
        chain.append(parent_id)
    if len(chain) > max_depth:
        return [f"{entry_id}: depth {len(chain)} exceeds max_depth {max_depth}"]
    return []


def build_toc_tree(entries):
    """Build the nested tree from flat entries that passed validate_toc.

    Siblings keep their list order. number (1.1.2), level, is_leaf and id
    (s1-1-2) come from the position in the tree; the LLM's ids only link
    children to parents.
    """
    children = {}
    for entry in entries:
        children.setdefault(entry["parent_id"], []).append(entry)

    def build(entry, path):
        kids = tuple(
            build(child, path + [i])
            for i, child in enumerate(children.get(entry["id"], []), 1)
        )
        return TocNode(
            id="s" + "-".join(map(str, path)),
            number=".".join(map(str, path)),
            level=len(path),
            title=entry["title"],
            description=entry["description"],
            children=kids,
            is_leaf=not kids,
        )

    return [build(entry, [i]) for i, entry in enumerate(children.get(None, []), 1)]


def flatten_tree(tree):
    """Return every node in pre-order, which is document order."""
    nodes = []
    for node in tree:
        nodes.append(node)
        nodes.extend(flatten_tree(node.children))
    return nodes


def save_toc(path, tool, doc_type, tree):
    """Write the tree as a nested JSON object: {tool, document_type, sections}."""
    data = {"tool": tool.name, "document_type": doc_type, "sections": [_node_to_dict(n) for n in tree]}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_toc(path):
    """Read a file written by save_toc and return its top-level nodes."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [_node_from_dict(d) for d in data["sections"]]


def _node_to_dict(node):
    return {
        "id": node.id,
        "number": node.number,
        "level": node.level,
        "title": node.title,
        "description": node.description,
        "children": [_node_to_dict(c) for c in node.children],
    }


def _node_from_dict(d):
    children = tuple(_node_from_dict(c) for c in d["children"])
    return TocNode(
        id=d["id"],
        number=d["number"],
        level=d["level"],
        title=d["title"],
        description=d["description"],
        children=children,
        is_leaf=not children,
    )
