# Phase 1: Synthetic Legal Document Generation — Design

## 1. Goal

Build a configurable console application that generates 20 synthetic software legal documents: 5 fictional tools × 4 document types. Each document is an HTML file with a matching JSON table of contents. Every document contains 2–3 intentionally planted quality issues, recorded in a separate answer key. The dataset is the input for later phases (parsing, RAG, report generation), so the documents must be realistic in length and structure, valid HTML/JSON, and come with exact knowledge of which issues are real.

## 2. Requirements checklist

| Requirement (task) | Where handled |
|---|---|
| 20 docs = 5 tools × 4 docs | Config `num_tools`, `docs_per_tool`; Flow `main` |
| Types chosen from the 6 listed | Config `doc_types`; `select_doc_types` (random, balanced) |
| Output layout `/data/toolN/toc_*.json` + `*.html` | §5 Data layout; `save_toc`, `write_outputs` |
| TOC is a valid JSON object, not a string | `save_toc` writes a nested JSON tree |
| Programmatic HTML parsing/validation | §7; `validate_section`, `validate_document`, `validate.py` |
| Tool ideation: name, purpose, category, user base | `generate_tools` + schema |
| Tools are fictional (no prior LLM knowledge) | `prompts/tool_ideation.yaml` instruction |
| Random doc types per tool | `select_doc_types` |
| Tool description is persistent context | `tool.json`; passed to every TOC/section/judge/repair call |
| TOC by reasoning-capable model | Config `models.toc` (DeepSeek V4.1 Flash, reasoning effort high) |
| JSON output enforced via structured outputs | `call_llm` with strict `json_schema` on every call; `require_parameters` routes only to providers that enforce it (D39) |
| TOC deeper than 2 levels where realistic | TOC prompt depth guidance; `max_depth` = 4 |
| Sections by cost-effective model, one by one | Config `models.section` (Gemma 4 31B, reasoning off); leaf loop |
| Each section gets tool + all sections so far | `generate_section` system prompt |
| At least two different models | DeepSeek V4.1 Flash (ideation, TOC, judge), Gemma 4 31B (sections, repairs) |
| Price/performance-based model choice | §8 Decisions D1, D2, D30, D40; usage and cost recorded per document (D41) |
| Temperature used and configurable, variety | Config `temperature.*`; per-doc sampled ranges |
| 2–3 intentional issues per document | `assign_issues`; config `issues_per_doc` |
| Issues actually present | `issues_applied` check + post-assembly judge + repair loop |
| Realistic length (SLA-like) | Guide `typical_length` + word-count check; 12–25 leaves |
| Sections always HTML; assembled doc valid | Section HTML contract; `validate_section`, `validate_document` |
| No whole-document generation in one call | Leaf-by-leaf loop |
| Prompts in YAML, not inline strings | `prompts/*.yaml`, one per step |
| Detailed system/user prompts | Prompt files (§5); content outline in `generate_section` |
| No hard-coded fallbacks on failure | §7: retry, then stop; never placeholder text |
| Configurable for all parameters | `config.yaml` (§6) |
| Reproducible outputs | Global seed → per-doc seed; LLM `seed` param; pinned model snapshot and provider order (D39); metadata record |
| Basic HTML + JSON integrity validation | `validate.py data/` |

## 3. Flow

```
main(config_path):
    cfg     = load_config(config_path)
    guides  = load_style_guides(cfg.paths.guides_dir, cfg.generation.doc_types)
    prompts = load_prompts(cfg.paths.prompts_dir)
    run_rng = Random(cfg.seed)
    run_id  = timestamp()                                           # tags this run's usage entries
    summary = new RunSummary()

    try:
        tools     = load_or_generate_tools(cfg, prompts, run_id)    # {"tool1": Tool, ...}
        selection = select_doc_types(cfg.generation.num_tools,
                                     cfg.generation.docs_per_tool,
                                     cfg.generation.doc_types, run_rng)  # {"tool1": [doc_type, ...]}

        for tool_id, tool in tools:
            for doc_type in selection[tool_id]:
                if document_complete(cfg, tool_id, doc_type):
                    continue                                          # resume
                flags = generate_document(cfg, prompts, tool_id, tool,
                                          doc_type, guides[doc_type], run_id)
                summary.add(tool_id, doc_type, flags)

    except BudgetExhausted as e:      # out of credits (402) or max 429 wait exceeded
        summary.stopped("budget", e)
    except GenerationFailed as e:     # 3 failed attempts on one call
        summary.stopped("failure", e)  # e.g. "tool3/service_level_agreement: section 4.2 failed validation 3 times"
    finally:
        summary.usage = run_usage(cfg.paths.cache_dir, run_id)      # this run's calls, all ledgers
        write_run_summary(cfg.paths.log_dir, summary)

    exit(0 if summary.completed else 1)


generate_document(cfg, prompts, tool_id, tool, doc_type, guide, run_id) -> DocFlags:
    rng          = doc_rng(cfg.seed, tool_id, doc_type)
    temp_toc     = rng.uniform(*cfg.temperature.toc_range)
    temp_section = rng.uniform(*cfg.temperature.section_range)
    cache        = doc_cache_dir(cfg, tool_id, doc_type)
    ledger       = Ledger(cache / "usage.jsonl", run_id)        # every LLM attempt for this document
    llm_seed     = rng.randint(0, 2**31 - 1)

    # Step 1: TOC
    toc_path = cfg.paths.data_dir / tool_id / f"toc_{doc_type}.json"
    if exists(toc_path):
        tree = load_toc(toc_path)
    else:
        flat_raw = with_attempts(f"{tool_id}/{doc_type}: TOC",
                       produce  = generate_toc(tool, doc_type, guide, temp_toc, llm_seed, cfg, prompts),
                       validate = validate_toc(_, cfg),
                       ledger   = ledger)
        tree = build_toc_tree(flat_raw)
        save_toc(toc_path, tool, doc_type, tree)

    nodes      = flatten_tree(tree)                      # pre-order, document order
    leaves     = [n for n in nodes if n.is_leaf]
    assignment = assign_issues(leaves, cfg.generation.issue_types,
                               cfg.generation.issues_per_doc, rng)   # {section_id: issue_type}

    # Step 2: sections (leaves only)
    sections = load_cached_sections(cache)               # {section_id: SectionResult}
    for leaf in leaves:
        if leaf.id in sections:
            continue
        sections[leaf.id] = with_attempts(f"{tool_id}/{doc_type}: section {leaf.number}",
            produce  = generate_section(tool, doc_type, leaf, guide, nodes, sections,
                                        assignment.get(leaf.id), temp_section, llm_seed, cfg, prompts),
            validate = validate_section(_, leaf, guide, assignment.get(leaf.id), leaves, cfg),
            ledger   = ledger)
        save_cached_section(cache, leaf.id, sections[leaf.id])

    # Assembly
    html = assemble_document(tool, doc_type, tree, sections)
    raise_if_errors(validate_document(html, tree, cfg))

    # Step 3: judge + repair (shared loop, max cfg.retry.repair_rounds)
    round = load_repair_round(cache)
    loop:
        verdict = with_attempts(f"{tool_id}/{doc_type}: judge",
                      produce  = judge_document(tool, doc_type, html, nodes, sections,
                                                assignment, cfg, prompts),
                      validate = validate_verdict(_, assignment, leaves),
                      ledger   = ledger)
        to_fix = sections_to_repair(verdict, assignment)  # missing planted ∪ sections with unintended
        if to_fix is empty or round == cfg.retry.repair_rounds:
            break
        for section_id in to_fix:
            leaf = node_by_id(nodes, section_id)
            sections[section_id] = with_attempts(f"{tool_id}/{doc_type}: repair {leaf.number}",
                produce  = repair_section(tool, doc_type, leaf, guide, html,
                                          assignment.get(section_id),
                                          verdict.unintended_for(section_id),
                                          temp_section, llm_seed, cfg, prompts),
                validate = validate_section(_, leaf, guide, assignment.get(section_id), leaves, cfg),
                ledger   = ledger)
            save_cached_section(cache, section_id, sections[section_id])
        html = assemble_document(tool, doc_type, tree, sections)
        raise_if_errors(validate_document(html, tree, cfg))
        round += 1
        save_repair_round(cache, round)

    write_outputs(cfg, tool_id, doc_type, html, nodes, sections, assignment, verdict,
                  temps = {toc: temp_toc, section: temp_section, judge: cfg.temperature.judge},
                  seeds = {global: cfg.seed, llm: llm_seed}, repair_rounds = round,
                  usage = sum_usage(read_usage(ledger.path)))      # all runs of this document
    return flags_from(verdict)   # not_verified planted issues, leftover unintended issues
```

## 4. Functions

Shared types: `Tool {name, purpose, category, typical_user_base}`; `TocNode {id, number, level, title, description, children, is_leaf}`; `SectionResult {html, issues_applied: [{issue_type, description, conflicts_with?}]}`; `Verdict {planted: [{section_id, issue_type, present, evidence}], unintended: [{section_id, issue_type, description}]}`; `Usage {model, provider, prompt_tokens, completion_tokens, reasoning_tokens, cost_usd}`; `Ledger {path, run_id}`.

### Setup

**`load_config(path) -> Config`**: load `config.yaml` and check required keys and value ranges.
```
read YAML; check every key in §6 exists
check docs_per_tool <= len(doc_types); issues_per_doc[1] <= len(issue_types)
check min(leaf_range) >= issues_per_doc[1] + 1          # room for one issue per leaf + an earlier leaf for contradiction
return Config
```

**`load_style_guides(guides_dir, doc_types) -> dict[str, StyleGuide]`**: load one YAML guide per configured type.
```
for t in doc_types: read guides_dir/f"{t}.yaml"; check required fields (§5); store
fail if any guide is missing
```

**`load_prompts(prompts_dir) -> dict[str, PromptTemplate]`**: load one prompt file per step.
```
for step in [tool_ideation, toc, section, repair, judge]: read prompts_dir/f"{step}.yaml" -> {system, user}
check every template has its required placeholders
```

### LLM access

**`call_llm(model_cfg, messages, schema, temperature, seed) -> (dict, Usage)`**: one chat completions call with strict `json_schema` output, fixed provider routing and usage reporting; handles rate limits and out-of-credit.
```
total_wait = 0
loop:
    response = POST chat/completions (model = model_cfg.id, messages, temperature, seed,
                                      response_format = json_schema(schema, strict=true),
                                      reasoning = model_cfg.reasoning,
                                      provider = {order: model_cfg.providers,
                                                  allow_fallbacks: cfg.api.allow_fallbacks,
                                                  require_parameters: cfg.api.require_parameters},
                                      usage = {include: true})
    if status == 402: raise BudgetExhausted("out of credits")
    if status == 429:
        wait = Retry-After header if present else backoff_base * 2**n
        if total_wait + wait > cfg.retry.max_total_wait_s: raise BudgetExhausted
        sleep(wait); total_wait += wait; continue        # does NOT count as an attempt
    if other HTTP/API error: raise CallError             # incl. no listed provider available
    usage = Usage(model_cfg.id, response.provider, response.usage.prompt_tokens,
                  response.usage.completion_tokens,
                  response.usage.completion_tokens_details.reasoning_tokens,
                  response.usage.cost)
    return parse_json(response.content), usage           # parse error -> CallError(usage): the call was billed
```

**`with_attempts(label, produce, validate, ledger, max_attempts=cfg.retry.max_attempts) -> result`**: retry wrapper for content errors; records every attempt's usage.
```
for attempt in 1..max_attempts:
    try: result, usage = produce()
    except CallError as e:
        if e.usage: append_usage(ledger, label, attempt, ok = false, e.usage)
        log(label, attempt, e); continue
    errors = validate(result)
    append_usage(ledger, label, attempt, ok = no errors, usage)
    if no errors: return result
    log(label, attempt, errors)
raise GenerationFailed(f"{label} failed validation {max_attempts} times")
```
`produce` returns `(result, usage)` and `validate` receives only `result`. `BudgetExhausted` passes through untouched (402 and 429 responses are not billed).

### Usage ledger

**`append_usage(ledger, label, attempt, ok, usage)`**: append one JSON line `{run_id, label, attempt, ok, model, provider, prompt_tokens, completion_tokens, reasoning_tokens, cost_usd, at}` to `ledger.path`.

**`read_usage(path) -> list[UsageEntry]`**: all entries of one ledger; empty if the file doesn't exist.

**`sum_usage(entries) -> UsageTotals`**: `{calls, failed_calls, prompt_tokens, completion_tokens, reasoning_tokens, cost_usd, by_model: {model: same totals}, providers: [distinct providers used]}`.

**`run_usage(cache_dir, run_id) -> UsageTotals`**: `sum_usage` over the entries with this `run_id` in every `usage.jsonl` under `cache_dir`.

### Tool ideation

**`load_or_generate_tools(cfg, prompts, run_id) -> dict[str, Tool]`**: reuse `tool.json` files if all exist, else generate.
```
if all data/tool{i}/tool.json exist for i in 1..num_tools: load and return
tools = with_attempts("tool ideation", produce = generate_tools(cfg, prompts),
                      validate = validate_tools(_, cfg.generation.num_tools),
                      ledger   = Ledger(cfg.paths.cache_dir / "tool_ideation" / "usage.jsonl", run_id))
for i, tool in enumerate(tools, 1): write data/tool{i}/tool.json
return {"tool{i}": tool}
```

**`generate_tools(cfg, prompts) -> (list[Tool], Usage)`**: one call that generates all tools, so each tool is designed to differ from the ones before it.
```
messages    = render(prompts.tool_ideation, num_tools)   # fictional, clearly different categories
schema      = {tools: [Tool] (exactly num_tools items)}
data, usage = call_llm(cfg.models.tool_ideation, messages, schema,
                       cfg.temperature.tool_ideation, seed = cfg.seed)
return data.tools, usage
```

**`validate_tools(tools, num_tools) -> list[str]`**: count == num_tools, names unique (case-insensitive), no empty fields.

### Planning

**`select_doc_types(num_tools, docs_per_tool, doc_types, rng) -> dict[str, list[str]]`**: random but balanced type choice.
```
total = num_tools * docs_per_tool
quota = {t: total // len(doc_types)}; give +1 to (total % len(doc_types)) types picked by rng
for each tool_id:
    candidates = doc_types ordered by remaining quota desc, ties shuffled by rng
    pick first docs_per_tool distinct types; decrement quotas
check all quotas == 0
```

**`doc_rng(seed, tool_id, doc_type) -> Random`**: per-document RNG from a stable hash of `(seed, tool_id, doc_type)`, so resume and order changes don't change a document's draws.

**`assign_issues(leaves, issue_types, issues_per_doc, rng) -> dict[str, str]`**: code places the planted issues.
```
k     = rng.randint(issues_per_doc.min, issues_per_doc.max)
types = rng.sample(issue_types, k)                       # distinct types
free  = list(leaves)
if "contradiction" in types: assign it to rng.choice(free[1:]) (needs an earlier leaf); remove it from free
for each remaining type: assign to rng.choice(free); remove
return {section_id: issue_type}                          # max one issue per section
```

### Step 1: TOC

**`generate_toc(tool, doc_type, guide, temperature, seed, cfg, prompts) -> (list[RawTocEntry], Usage)`**: reasoning model produces a flat TOC with section descriptions.
```
messages    = render(prompts.toc, tool_json, doc_type, guide.purpose, guide.scope,
                     guide.core_topics, guide.optional_topics, guide.tone_and_conventions,
                     max_depth, leaf_range)              # schema-only example; depth guidance, not forced
schema      = {entries: [{id, parent_id|null, title, description}]}   # list order = document order
data, usage = call_llm(cfg.models.toc, messages, schema, temperature, seed)
return data.entries, usage
```

**`validate_toc(entries, cfg) -> list[str]`**: ids unique; every `parent_id` null or existing; no cycles; parents appear before children; title and description non-empty; depth <= `max_depth`; leaf count within `leaf_range`.

**`build_toc_tree(entries) -> list[TocNode]`**: build the nested tree; code computes `number` (1, 1.1, 1.1.2), `level`, `is_leaf`, and a stable `id` (`s1-1-2`).

**`flatten_tree(tree) -> list[TocNode]`**: pre-order traversal used by the generation loop.

**`save_toc(path, tool, doc_type, tree)`** / **`load_toc(path) -> list[TocNode]`**: write/read the nested JSON tree (§5).

### Step 2: sections

**`generate_section(tool, doc_type, leaf, guide, nodes, sections, assigned_issue, temperature, seed, cfg, prompts) -> (SectionResult, Usage)`**: section model writes one leaf section as HTML.
```
system = render(prompts.section.system, tool_json, doc_type, guide.tone_and_conventions,
                toc_outline(nodes),                                  # numbers + titles
                sections_so_far(nodes, sections))                     # all earlier leaves, numbered, in order
user   = render(prompts.section.user, leaf.number, leaf.title, leaf.description,
                guide.typical_length.section_words, html_contract,
                issue_instruction(assigned_issue))                    # or "introduce no errors"
schema = {html: string, issues_applied: [{issue_type, description, conflicts_with|null}]}
return call_llm(cfg.models.section, [system, user], schema, temperature, seed)   # (SectionResult, Usage)
```

**`validate_section(result, leaf, guide, assigned_issue, leaves, cfg) -> list[str]`**: section-level checks (§7).

**`load_cached_sections(cache) -> dict`** / **`save_cached_section(cache, section_id, result)`**: per-section resume cache.

### Assembly

**`assemble_document(tool, doc_type, tree, sections) -> str`**: build the full HTML document.
```
<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{tool.name} {Doc Type}</title></head>
<body><article><h1 class="doc-title">{tool.name} {Doc Type}</h1>
for node in tree (recursive):
    <section id="{node.id}">
      <h{node.level+1} class="toc-heading">{node.number} {node.title}</h{node.level+1}>
      if leaf: sections[node.id].html
      else:    recurse into children (no intro text)
    </section>
</article></body></html>
```

**`validate_document(html, tree, cfg) -> list[str]`**: document-level checks (§7). Assembly is deterministic, so a failure here is a bug: raise `GenerationFailed`.

### Step 3: judge and repair

**`judge_document(tool, doc_type, html, nodes, sections, assignment, cfg, prompts) -> (Verdict, Usage)`**: reasoning model checks planted issues and finds unintended ones, with the full document as context.
```
messages = render(prompts.judge, tool_json, doc_type, html,
                  planted = [{section_id, number, issue_type, model's description}],
                  issue_type_definitions)
schema   = Verdict
return call_llm(cfg.models.judge, messages, schema, cfg.temperature.judge, seed = cfg.seed)   # (Verdict, Usage)
```

**`validate_verdict(verdict, assignment, leaves) -> list[str]`**: exactly one `planted` entry per assigned issue; all `section_id`s exist among leaves.

**`sections_to_repair(verdict, assignment) -> list[str]`**: ids where a planted issue is `present = false`, plus ids with any unintended issue; document order, no duplicates.

**`repair_section(tool, doc_type, leaf, guide, html, assigned_issue, unintended, temperature, seed, cfg, prompts) -> (SectionResult, Usage)`**: regenerate one section with the whole document as context and output only that section.
```
system = render(prompts.repair.system, tool_json, doc_type, guide.tone_and_conventions, full_document = html)
user   = render(prompts.repair.user, leaf.number, leaf.title, leaf.description,
                guide.typical_length.section_words, html_contract,
                issue_instruction(assigned_issue), fix_list = unintended)
return call_llm(cfg.models.section, [system, user], SectionResult schema, temperature, seed)   # (SectionResult, Usage)
```

**`load_repair_round(cache) -> int`** / **`save_repair_round(cache, round)`**: persist the repair counter for resume.

### Outputs and resume

**`write_outputs(cfg, tool_id, doc_type, html, nodes, sections, assignment, verdict, temps, seeds, repair_rounds, usage)`**: write `{doc_type}.html`, then `meta_{doc_type}.json` last (meta marks the document complete).
```
planted    = for each assigned issue: {section_id, number, issue_type, description,
                                       conflicts_with, status: "verified" | "not_verified"}
unintended = leftover verdict.unintended, each labeled "unintended"
write meta {tool_id, doc_type, models, temps, seeds, planted, unintended, repair_rounds,
            leaf_count, word_count, usage, created_at}    # usage: UsageTotals over all runs of this doc
```

**`document_complete(cfg, tool_id, doc_type) -> bool`**: `toc_*.json`, `*.html` and `meta_*.json` all exist.

**`write_run_summary(log_dir, summary)`**: completed docs, stop reason, flagged docs (any `not_verified` or leftover unintended issue), and this run's usage totals per model (`summary.usage`).

### Standalone validator (`validate.py data/`)

**`validate_data_dir(data_dir) -> Report`**: check every tool folder and print a report; non-zero exit on any failure.
```
for each toolN folder:
    check tool.json loads and has all Tool fields
    for each toc_*.json:
        check valid JSON, tree structure, numbering consistent with nesting, depth <= max_depth
        check matching {doc_type}.html exists -> validate_html_file(html_path, toc)
        check matching meta_{doc_type}.json exists and loads
print per-file PASS/FAIL with reasons
```

**`validate_html_file(path, toc) -> list[str]`**: run `validate_document` against the TOC loaded from disk.

## 5. Data and output layout

```
config.yaml
style_guides/
  privacy_policy.yaml, terms_of_service.yaml, data_processing_agreement.yaml,
  service_level_agreement.yaml, security_whitepaper.yaml, compliance_certifications.yaml
prompts/
  tool_ideation.yaml, toc.yaml, section.yaml, repair.yaml, judge.yaml   # each: {system, user}
data/
  tool1/
    tool.json                       # Tool description (persistent context)
    toc_privacy_policy.json         # nested TOC tree
    privacy_policy.html             # assembled document
    meta_privacy_policy.json        # metadata + answer key
    ...
  tool2/ ... tool5/
.cache/toolN/{doc_type}/
  sections/{section_id}.json        # SectionResult per finished leaf
  repair_round.json
  usage.jsonl                       # one line per LLM attempt (D41)
.cache/tool_ideation/
  usage.jsonl                       # tool ideation attempts
logs/
  run_{timestamp}.log, run_summary_{timestamp}.json
```

**`toc_{doc_type}.json`**
```
{ "tool": "<name>", "document_type": "<doc_type>",
  "sections": [ { "id": "s1", "number": "1", "level": 1, "title": "...", "description": "...",
                  "children": [ { "id": "s1-1", "number": "1.1", ... "children": [] } ] } ] }
```
No issue information in the TOC or HTML (answer key lives only in meta).

**Style guide YAML**
```yaml
document_type: privacy_policy
purpose: "1-2 sentences: what this document is for and between whom"
scope: "what such documents cover and exclude, and the main ways they differ"
core_topics:
  - name: "..."
    description: "1 sentence"
    content_points: ["short phrase"]
optional_topics:
  - name: "..."
    description: "1 sentence"
    content_points: ["short phrase"]
tone_and_conventions: "..."
typical_length:
  section_words: [min, max]     # per leaf section, from research
```

**Section HTML contract** (in section/repair prompts): one wrapper `<div>`; body tags only (`p`, lists, tables, `strong`, `em`, `a`, `br`, `blockquote`, `h5`, `h6` for minor sub-labels); no `html/head/body/section/script/style`, no `h1–h4`, no `toc-heading` class. Planted formatting errors must stay within valid markup.

## 6. Config

| Key | Default | Description |
|---|---|---|
| `seed` | 42 | Global seed; per-doc seeds derived from it |
| `paths.data_dir` | `data` | Output root |
| `paths.guides_dir` | `style_guides` | Style guide YAMLs |
| `paths.prompts_dir` | `prompts` | Prompt YAMLs |
| `paths.cache_dir` | `.cache` | Section cache for resume |
| `paths.log_dir` | `logs` | Logs and run summary |
| `api.base_url` | `https://openrouter.ai/api/v1` | OpenRouter chat completions |
| `api.api_key_env` | `OPENROUTER_API_KEY` | Env var holding the key |
| `api.timeout_s` | 120 | Request timeout |
| `api.require_parameters` | true | Route only to providers that support every request parameter (D39) |
| `api.allow_fallbacks` | false | Never use providers outside `models.*.providers` (D39) |
| `models.tool_ideation` | `deepseek/deepseek-v4.1-flash-1017`, reasoning effort high | Tool ideation |
| `models.toc` | `deepseek/deepseek-v4.1-flash-1017`, reasoning effort high | TOC |
| `models.section` | `google/gemma-4-31b-it`, reasoning off | Sections and repairs |
| `models.judge` | `deepseek/deepseek-v4.1-flash-1017`, reasoning effort high | Judge (must differ from section model) |
| `models.*.providers` | DeepSeek: `deepinfra/fp8`, `inference-net/fp8`, `nebius/fp8`; Gemma: `crusoe/bf16`, `parasail/fp8`, `deepinfra/fp8` | Provider order per model, tried in sequence (D39) |
| `temperature.tool_ideation` | 0.95 | Fixed, from 0.9–1.0 |
| `temperature.toc_range` | [0.7, 0.9] | Sampled per document |
| `temperature.section_range` | [0.5, 0.7] | Sampled per document; also used for repairs |
| `temperature.judge` | 0.2 | Fixed |
| `generation.num_tools` | 5 | Tools to generate |
| `generation.docs_per_tool` | 4 | Documents per tool |
| `generation.doc_types` | the 6 task types | Pool for `select_doc_types` |
| `generation.issue_types` | contradiction, ambiguity, typo_formatting, inconsistent_terminology | Planted issue pool |
| `generation.issues_per_doc` | [2, 3] | Planted issues per document |
| `toc.max_depth` | 4 | Max TOC depth (validated) |
| `toc.leaf_range` | [12, 25] | Allowed leaf sections (validated) |
| `validation.section_word_tolerance` | 0.2 | Allowed deviation from `section_words` |
| `retry.max_attempts` | 3 | Attempts for content/API errors per call |
| `retry.repair_rounds` | 2 | Shared judge/repair rounds per document |
| `retry.backoff_base_s` | 2 | Base for exponential 429 backoff |
| `retry.max_total_wait_s` | 600 | Max cumulative 429 wait per call before clean stop |

## 7. Validation and failure handling

**Tool ideation**: count, unique names, non-empty fields.

**TOC** (`validate_toc`, before saving): unique ids, valid `parent_id`s, no cycles, parents before children, non-empty title/description, depth <= `max_depth`, leaf count in `leaf_range`.

**Section** (`validate_section`, after every section/repair call):
- html5lib parse reports no errors
- single wrapper `<div>`, only allowed tags, no `toc-heading` class
- word count within `section_words` ± tolerance
- `issues_applied` has exactly the assigned issue type (or is empty if none assigned)
- for contradiction: `conflicts_with` names an earlier leaf

**Assembled document** (`validate_document`):
- html5lib parse reports no errors; exactly one `h1`
- nested `<section>` tree matches the TOC tree; ids unique
- each `toc-heading` text equals `"{number} {title}"`; no `toc-heading` without a TOC entry
- every leaf section non-empty

**Judge**: one verdict per planted issue; section ids valid.

**Standalone**: `python validate.py data/` re-runs TOC and document checks from disk and prints a report.

**Failure rules**

| Situation | Behavior |
|---|---|
| HTTP 429 (per-minute) | Wait `Retry-After` or exponential backoff; not counted as an attempt; up to `max_total_wait_s` |
| HTTP 402 (out of credits) or max wait exceeded | Clean stop (`BudgetExhausted`); top up, rerun resumes |
| API error, JSON parse error, validation failure | Counts as an attempt; after 3, stop the whole run with a clear log line |
| No listed provider available (all down, or none supports a required parameter) | API error: counts as an attempt; after 3, stop; rerun resumes |
| Planted issue not found by judge | Regenerate that section (shared repair loop, max 2 rounds); then mark `not_verified` |
| Unintended mistake found by judge | Repair in the same loop; leftovers recorded as `unintended`, document flagged |
| Any failure | Never substitute placeholder or hard-coded text |

**Resume**: tools reused from `tool.json`; type selection recomputed from seed; documents with `meta_*.json` skipped; TOC reused if saved; finished sections loaded from cache; repair round counter persisted; usage ledger persisted, so a document's meta covers every run it took.

## 8. Decisions

| # | Decision | Alternatives | Reason |
|---|---|---|---|
| D1 | TOC → DeepSeek V4.1 Flash (`-1017` snapshot, paid), reasoning effort high | Nemotron 3.5 Super VL (free); GLM-5.3-Flash; Claude Haiku 5.5; GPT-6 Luna | Best price/performance among reasoning models that support strict JSON, `seed` and `temperature` on OpenRouter (2026-11-04): Intelligence Index v5 29 at high effort vs 14 for Nemotron, at a lower cost per benchmark task ($0.46 vs $0.54, Nemotron is very verbose). About $0.10 / $0.29 per 1M input/output tokens on the first listed provider, 1M context, ~189 tokens/s. The dated snapshot keeps runs reproducible. Haiku 5.5 and GPT-6 Luna don't accept `temperature` on OpenRouter; GLM-5.3-Flash is slow (~59 tokens/s). |
| D2 | Sections → Gemma 4 31B (paid), thinking off | Gemma 4 31B (free); other cost-effective models | The free endpoint (Google AI Studio only) doesn't support strict structured outputs, needed for `{html, issues_applied}`; most paid providers do. 262K context, enough for all previous sections in every call. Token-efficient, and good writing quality matters most for realistic legal text. About $0.14 / $0.40 per 1M. Thinking off: faster, no reasoning needed to write a section. A different model family from the judge (D19). |
| D3 | Tool ideation uses DeepSeek (the TOC and judge model) | Section model | Reasoning helps plan clearly distinct tools. One reasoning model for ideation, TOC and judge keeps one config shape. |
| D4 | One tool-ideation call for all tools | One call per tool | Saves calls and the model sees previous tools in the same output. Earlier items are things to avoid: when writing tool 3, tools 1 and 2 are "already taken", so context works against repetition. |
| D5 | No real examples in prompts; TOC prompt has a schema-only example | Real example; no example | A real example points the same way as the task and pulls the model toward copying structure and phrasing. A schema-only example shows the format without copying and clarifies field meaning. |
| D6 | Temperatures: ideation fixed ~0.9–1.0; TOC 0.7–0.9 per doc; sections 0.5–0.7 per doc; judge 0.2 | Single temperature | Ideation: diversity is the point, output is small and schema-protected, one call so a fixed value is enough. TOC: structure should differ, but must stay a coherent hierarchy. Sections: long text needs coherence; variety comes from tools and TOCs; too low gives stock phrases, too high gives drift, broken HTML, or accidental errors mixed with intended ones. Judge: near-deterministic with slight flexibility. |
| D7 | Temperature only, no top_p | Configurable top_p | One knob is enough; easier to reason about. |
| D8 | LLM returns a flat TOC; code saves it nested and loops over a flat list | Store flat; nested from LLM | Readable nested file; simple loop. |
| D9 | Code computes section numbers from the tree | LLM provides | Always consistent; one less LLM check. |
| D10 | TOC entries carry a 1–2 sentence description; section calls get only that plus tone conventions | Full guide per section | Cuts repeated input tokens (~1M per run) and gives each section a precise, focused instruction. |
| D11 | No intro text for parent sections | Short parent intros | Fewer calls; no filler text; cleaner chunks. |
| D12 | TOC limits: `max_depth` 4, leaves 12–25, validated; depth guided by prompt, not forced | No limits; forced min depth | Predictable call count; room for planted issues; 12–25 leaves closer to real length; depth 4 avoids fragments. Depth is requested via prompt, not forced on every document. |
| D13 | Doc types: random but balanced | Pure random | Every type covered; fairer later evaluation. |
| D14 | Code assigns issues after the TOC | TOC model; section model | Reproducible with seed; guaranteed 2–3 count; control over placement. |
| D15 | Max one planted issue per section | Multiple | Issues spread out; easier verification. |
| D16 | Contradictions conflict with an earlier section | Within the section | Realistic; the judge sees the full document. |
| D17 | Planted issues recorded in a per-document metadata file | Inside TOC; inside HTML | Chosen so the answer key isn't revealed through the TOC or the HTML. |
| D18 | `tool.json` per tool + `meta_*.json` per document | — | Reproducibility record; answer key for Phase 5; tool context reusable. |
| D19 | Judge after assembly with a separate model (TOC model, 0.2); repair only affected sections, re-validate, re-judge, max 2 rounds; unverified → `not_verified` | Judge per section; no judge | Fewer calls saves tokens, and full context may catch other mistakes. Contradictions need full context. |
| D20 | Unintended mistakes are repaired in the same loop; leftovers recorded as `unintended` and flagged | Record only; ignore | Clean ground truth. |
| D21 | Sections-so-far in the system prompt | User prompt | Task recommends it. |
| D22 | Length: `typical_length` in style guides + word-count check | Prompt only; one config value | Document types differ in length. |
| D23 | Section HTML: body tags plus minor `h5/h6`; TOC headings marked with `class="toc-heading"` | h6 only; `<strong>` only | Keeps realistic markup. |
| D24 | Nested `<section>` elements | Flat sections | Mirrors the TOC tree; easier validation; better chunking later. |
| D25 | Assembled HTML: title + numbered headings, no in-page TOC | Add `<nav>` | No duplicated TOC; simpler later parsing. |
| D26 | Folders `tool1 … tool5` | Tool-name slug | Matches task example; no slug collisions. |
| D27 | Validate the TOC, every section, and the assembled document | Final check only | Catch errors early; cheap retries; final guarantee. |
| D28 | Standalone `validate.py data/` | Validation only inside generation | Clean answer to the "validation logic" deliverable; reviewers can run it themselves. |
| D29 | html5lib + explicit structural checks | Strict XML parse | Parses like a browser; each check is explicit. |
| D30 | OpenRouter paid models | Free models; direct provider APIs | Free Gemma has no strict JSON support. The free tier caps requests per day (50, or 1,000 after buying credits), which forces multi-day runs. A full paid run is estimated at about $1–1.5. One client for many models. |
| D31 | 429s: Retry-After or exponential backoff, not counted, up to a max total wait; max wait or 402 (out of credits) → clean stop and resume. Other errors use the 3 attempts. | Count 429s as attempts; stop immediately | Survives per-minute provider limits; running out of credit needs a top-up and resume, not retries; a 429 isn't a content error. |
| D32 | Out of credits detected from HTTP 402; no daily-limit detection | Local spend counter; keep daily-limit detection | Provider is source of truth; paid models have no daily request cap. |
| D33 | Retry 3 times, then stop the whole run and log clearly; never placeholder text | Skip doc and continue | Fail fast with a clear log; resume makes it cheap; repeated failures are likely systemic. Placeholder text is the hard-coded fallback the task forbids. |
| D34 | Resume per section | Per document | Saves paid calls; a stop (out of credits, 429 wait, failure) can hit mid-document. |
| D35 | Reproducibility: code seed + LLM `seed` param + metadata | Code seed only | Closer repeat runs; costs nothing where unsupported. |
| D36 | One prompt YAML per step | Single prompts file | Easy to find and edit; smaller diffs. |
| D37 | Config file only, no CLI overrides | Config + CLI | Single source of truth; simpler code. |
| D38 | Style guides have no "ambiguity points" field | Add the field | Reason not stated (see Open questions). |
| D39 | Provider routing: `require_parameters` + an ordered provider list per model (fp8/bf16 only, full context), no fallbacks outside the list | Free routing; single provider | Guarantees strict JSON, `seed` and `temperature` are honored; fewer quantization differences between runs; backups in the list survive one provider's outage. |
| D40 | DeepSeek reasoning effort `high` for ideation, TOC and judge | `max`; `medium` | Index 29 vs 33 at `max` for about 25% less cost and time per task ($0.46 vs $0.60; 10.4 vs 13.7 min). |
| D41 | Usage and cost recorded per LLM attempt in a per-document ledger (`usage.jsonl`), failed attempts included; summed into `meta_*.json` and the run summary | Don't record; run totals only; in-memory sums | Evidence for the price/performance choice; resume-safe, since a document can span runs; matches what OpenRouter bills, retries included. |

## 9. Open questions

1. **Resolved:** model IDs are `deepseek/deepseek-v4.1-flash-1017` and `google/gemma-4-31b-it`. The listed providers support strict `json_schema` and `seed` (OpenRouter endpoints API, 2026-11-04). The F7 probe confirms this in practice.
2. Check whether DeepSeek V4.1 Flash with reasoning on honors `temperature` (affects D6 for ideation, TOC, judge).
3. Confirm defaults not discussed: `section_word_tolerance` (0.2), `max_total_wait_s` (600), `backoff_base_s` (2), `timeout_s` (120), `temperature.tool_ideation` (0.95).
4. **Resolved:** paid models have no daily request cap (D30).
5. **Resolved:** no longer needed; out of credits is detected from HTTP 402 (D32).
6. Reason for D38 (dropping ambiguity points) is not stated.
7. Confirm the usage fields OpenRouter returns (`usage.cost`, `usage.completion_tokens_details.reasoning_tokens`, `provider`), needed for D41.

## Changelog

- **Goal** rewritten in design terms (was copied task text).
- **Requirements checklist** filled in, mapping every requirement and pitfall.
- **Flow**: fixed `extracted_mistakes`/`issues` name mismatch (now `assignment`); loop runs over leaves only, matching "no parent intro"; numbers moved to config; added judge/repair loop, resume, and stop handling from your answers.
- **TOC shape** unified: flat from LLM, nested on disk, flat for the loop; LLM `level` removed since code computes number/level/id.
- **Issue assignment** moved from `toc_generator` to new `assign_issues` (code, after TOC); `generate_section` now receives the assigned issue.
- **Section input** changed from the full guide to description + tone, matching your Decision.
- **TOC prompt example** changed from a real privacy policy to schema-only, resolving the conflict with "no examples".
- **`assemble_sections`** no longer returns `{html, issues_applied}`; issues go to `meta_*.json`.
- **Tool ideation** clarified as a single call with a fixed temperature.
- **Style guide YAML**: added `typical_length.section_words`; no ambiguity field.
- **Added** prompt files, judge + repair, rate-limit handling, per-section resume, balanced type selection, section HTML contract with `toc-heading` class, nested `<section>` layout, standalone validator details, and full config table, all based on your answers.
- **Added** `repair_round.json` so a stop mid-repair resumes with the correct round count, and a `load_config` check that `leaf_range` leaves room for all planted issues.
- **Decisions** keep your wording (shortened); new decisions use the reasons you selected.
- **Paid models (2026-11-04):**
  - **Model switch:** ideation, TOC and judge moved from Nemotron 3.5 Super VL (free) to DeepSeek V4.1 Flash. Sections moved to paid Gemma 4 31B, because the free Gemma endpoint has no strict structured outputs (D1–D3, D30, D34).
  - **New decisions:** provider routing (D39), reasoning effort (D40), usage ledger (D41).
  - **Function changes:**
    - New functions `append_usage`, `read_usage`, `sum_usage`, `run_usage`.
    - `call_llm` and every generator return `(result, Usage)`.
    - `with_attempts` takes a `ledger`; `load_or_generate_tools` and `generate_document` take `run_id`; `write_outputs` takes `usage`.
    - Meta and run summary include usage and cost.
  - **Config:** `api.require_parameters`, `api.allow_fallbacks` and `models.*.providers` added.
  - **Failure handling:** out of credits (402) replaces daily-limit detection (D31, D32).
  - **Open questions:** §9.1, 9.4 and 9.5 resolved; 9.2 now asks about DeepSeek; 9.7 added.
