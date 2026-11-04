# Phase 1 Implementation Plan

Implementation plan for `phase1_design.md` (source of truth). Conventions: Conventional Commits, branches `type/<short-name>`, GitHub pull requests merged with a merge commit (`--no-ff`).

## 1. Main branch bootstrap (before any feature branch)

Already on `main`: `phase1_design.md`, `rag_htec_project_specification.md`, `README.md`,
`CLAUDE.md` (commit `3449d79`). Nothing to add for the design doc.

Bootstrap commits go **directly to `main`** (scaffolding only, no PR). Every feature after
this goes through a PR. All commits are made by you.

**Status:** done. B1–B6 were committed as `201ebf8` and `a1b0c16`. The switch to paid
models (design D1–D3, D30–D32, D39–D41) was committed to `main` afterwards. Design, docs and
config changes stay on `main` until feature code starts (CLAUDE.md, Git).

### Commit B1: ignore rules first
Files: `.gitignore`, `.env.example`
```
.gitignore:   .cache/  logs/  .env  .venv/  venv/  __pycache__/  .pytest_cache/  style_guides/sources/
.env.example: OPENROUTER_API_KEY=
```
```
git add .gitignore .env.example
git commit -m "chore: Add gitignore and env example" -m "Ignore the resume cache, run logs, local .env, virtualenvs, Python
caches and the third-party documents copied to build the style
guides. .env.example documents the API key variable read through
python-dotenv."
```
**Why first:** creating the venv or running pytest after this commit can't accidentally
stage `.venv/`, `.cache/`, a real `.env` or `style_guides/sources/`.

### Commit B2: dependencies
File: `requirements.txt`. Only the direct dependencies, each pinned to the latest release
on PyPI as of 2026-11-04 (all resolve on Python 3.10 and 3.11):
```
requests==2.34.2
html5lib==1.1
PyYAML==6.0.3
python-dotenv==1.2.4
pytest==9.2.0
```
```
git add requirements.txt
git commit -m "chore: Add pinned Python requirements" -m "Pin only what the Phase 1 design needs: requests for the OpenRouter
client, html5lib for HTML validation, PyYAML for config, guides and
prompts, python-dotenv for the API key, and pytest for local tests."
```

### Commit B3: folder layout and default config
Files:
- `config.yaml` with every key and default from design §6. Model entries are
  `{id, reasoning}` because `call_llm` reads `model_cfg.reasoning`. `generation.doc_types`
  lists the six slugs `privacy_policy, terms_of_service, data_processing_agreement,
  service_level_agreement, security_whitepaper, compliance_and_certifications` (see Q3).
  Model IDs were first committed as the `:free` variants; they are now the paid models from
  design §6 (`deepseek/deepseek-v4.1-flash-1017`, `google/gemma-4-31b-it`), each with a
  provider list.
- `phase1/__init__.py` (empty package)
- `prompts/.gitkeep`, `data/.gitkeep`, `tests/.gitkeep`
- `.cache/` and `logs/` get no `.gitkeep`. They are ignored and created at runtime.
```
git add config.yaml phase1/__init__.py prompts/.gitkeep data/.gitkeep tests/.gitkeep
git commit -m "chore: Add Phase 1 folder layout and config" -m "Create the package, prompts, data and tests folders from the design
layout, and config.yaml with every key and default from the design
config table. No code reads it yet."
```

### Commit B4: style guides
Files: `style_guides/*.yaml` (6 guides). `style_guides/sources/` is ignored (Q11).
```
git add style_guides/*.yaml
git commit -m "docs: Add style guides for six document types" -m "One YAML guide per document type, built from public documents with
the guide generator prompt. Each has purpose, scope, topics, tone and
typical section length, as the design's style guide schema requires."
```

### Commit B5: generator prompts moved to Markdown
Files: delete `Yaml_file_generator_prompt.txt`; add `Yaml_file_generator_prompt.md` and
`YAML_generator_compliance_and_certifications.md`. The README/CLAUDE.md references to the
`.txt` file are fixed in B6, which edits both files anyway.
```
git rm Yaml_file_generator_prompt.txt
git add Yaml_file_generator_prompt.md YAML_generator_compliance_and_certifications.md
git commit -m "docs: Move style guide generator prompts to Markdown" -m "Replace the .txt prompt with a Markdown version and add the separate
prompt for Compliance & Certifications, whose sources are spread over
many pages."
```

### Commit B6: README stub and implementation plan
Files: `README.md` (purpose, setup with venv + `pip install -r requirements.txt` +
`cp .env.example .env`, `python -m pytest`, `python generate.py config.yaml`,
`python validate.py data/`, with the last two marked as not implemented yet, and links to
the `.md` generator prompts), `CLAUDE.md` (current state, the section-model open issue,
model IDs, layout, setup + test commands, `.md` prompt references), `IMPLEMENTATION_PLAN.md`.
```
git add README.md CLAUDE.md IMPLEMENTATION_PLAN.md
git commit -m "docs: Add setup instructions and Phase 1 plan" -m "README gets setup, test and run commands and links to the Markdown
generator prompts. CLAUDE.md records the model IDs, the open issue
with strict structured outputs on the free section model, and the
setup commands. IMPLEMENTATION_PLAN.md splits the Phase 1 design
into feature branches with steps, tests and done criteria."
```
Then `git push origin main`.

**Order rationale:** ignore rules (B1) come before anything that creates local files. Then
dependencies (B2), so the venv can be built. Then layout and config (B3), which describe
the design. Then content assets (B4, B5). Docs come last (B6) because the README refers to
files that now exist.

## 2. Feature breakdown

Code layout: one module per design §4 group under `phase1/`, with thin `generate.py` and
`validate.py` at the root. The shared types `Tool`, `TocNode`, `SectionResult` and `Verdict`
live in `phase1/datatypes.py`, each added by the first feature that needs it. LLM-calling
modules call `llm.call_llm(...)` through the module, so tests swap it with one
`monkeypatch.setattr` from a `fake_llm` fixture in `tests/conftest.py`. Every step leaves
`python -m pytest` green. The test levels (unit tests, model probe, smoke run, full run) are
defined in design §10.

Each branch starts from an up-to-date `main` once its dependencies are merged:
`git checkout main && git pull && git checkout -b <branch>`.

---

### F1 `feat/config-loading`
- **From:** `main` after bootstrap · **Depends on:** bootstrap
- **Goal:** load and check `config.yaml`, style guides and prompt templates.
- **Functions:** `load_config(path) -> Config`, `load_style_guides(guides_dir, doc_types) -> dict[str, StyleGuide]`, `load_prompts(prompts_dir) -> dict[str, PromptTemplate]`
- **Files:** `phase1/config.py`, `tests/test_config.py`
- **Steps:** see §4.
- **Local test (no API):** the real `config.yaml`, `config.smoke.yaml` and `style_guides/`, plus broken copies in `tmp_path`, plus prompt files written in `tmp_path`.
- **Real API:** none.
- **Done:** both real configs and all 6 guides load; every missing key, bad range, missing guide, missing guide field and missing placeholder gives an error that names it; pytest is green.

### F2 `feat/planning`
- **From:** `main` after F1 · **Depends on:** F1 (tests build a cfg from it)
- **Goal:** seeded, balanced document-type selection and planted-issue placement.
- **Functions:** `select_doc_types(num_tools, docs_per_tool, doc_types, rng) -> dict[str, list[str]]`, `doc_rng(seed, tool_id, doc_type) -> Random`, `assign_issues(leaves, issue_types, issues_per_doc, rng) -> dict[str, str]`
- **Files:** `phase1/planning.py`, `tests/test_planning.py`
- **Steps:**
  1. `doc_rng` from a stable hash (`hashlib`) → `feat(planning): Add per-document seeded RNG`
  2. `select_doc_types` with quotas → `feat(planning): Select balanced document types`
  3. `assign_issues` → `feat(planning): Assign planted issues to leaves`
- **Local test:** pure functions. For 5×4 over 6 types the quotas are 3/3/3/3/4/4 and each tool gets 4 distinct types. Same seed gives the same output. `doc_rng` doesn't depend on call order. The planted issue count stays within `issues_per_doc` with distinct types and at most one per leaf. A contradiction never lands on the first leaf (checked over many seeds).
- **Real API:** none.
- **Done:** all of the above pass for many seeds.

### F3 `feat/toc-tree`
- **From:** `main` after F1 · **Depends on:** F1
- **Goal:** validate the flat LLM TOC, build the nested tree, and save/load it.
- **Functions:** `validate_toc(entries, cfg) -> list[str]`, `build_toc_tree(entries) -> list[TocNode]`, `flatten_tree(tree) -> list[TocNode]`, `save_toc(path, tool, doc_type, tree)`, `load_toc(path) -> list[TocNode]`
- **Files:** `phase1/toc.py`, `phase1/datatypes.py` (`TocNode`), `tests/test_toc.py`, `tests/fixtures/toc_entries.json`
- **Steps:**
  1. `TocNode` + `build_toc_tree` (number, level, `is_leaf`, `s1-1-2` ids) → `feat(toc): Build numbered TOC tree from flat entries`
  2. `flatten_tree` → `feat(toc): Flatten TOC tree in document order`
  3. `validate_toc` → `feat(toc): Validate flat TOC entries`
  4. `save_toc` / `load_toc` in the §5 format → `feat(toc): Save and load nested TOC JSON`
- **Local test:** fixture entries 3–4 levels deep. Broken variants: duplicate id, unknown parent, cycle, child before parent, depth 5, too few or too many leaves, empty title. Save/load round-trip keeps the same tree, and the file is a JSON object, not a string.
- **Real API:** none.
- **Done:** fixture round-trip passes; each broken variant is reported.

### F4 `feat/html-checks`
- **From:** `main` after F3 · **Depends on:** F1, F3
- **Goal:** section-level and document-level HTML checks, plus deterministic assembly.
- **Functions:** `validate_section(result, leaf, guide, assigned_issue, leaves, cfg) -> list[str]`, `assemble_document(tool, doc_type, tree, sections) -> str`, `validate_document(html, tree, cfg) -> list[str]`
- **Files:** `phase1/sections.py` (`validate_section` only), `phase1/assembly.py`, `phase1/datatypes.py` (`SectionResult`, `Tool`), `tests/test_sections.py`, `tests/test_assembly.py`, `tests/fixtures/sections/*.html`
- **Steps:**
  1. `validate_section` markup checks (html5lib errors, single wrapper `<div>`, allowed tags, no `toc-heading`) → `feat(sections): Check section HTML contract`
  2. Word count ± tolerance, `issues_applied` type, and `conflicts_with` pointing to an earlier leaf → `feat(sections): Check section length and issues`
  3. `assemble_document` → `feat(assembly): Assemble nested HTML document`
  4. `validate_document` → `feat(assembly): Validate assembled document`
- **Local test:** good and bad fixture sections (an `h3`, `<script>`, two wrappers, a `toc-heading` class, too short, wrong issue type, contradiction pointing at a later leaf). Assembling the F3 fixture tree with fixture sections passes `validate_document`. Tampered copies fail: missing `<section>`, wrong heading text, two `h1`, empty leaf.
- **Real API:** none.
- **Done:** fixtures behave as listed; assembled output parses with no html5lib errors.

### F5 `feat/outputs`
- **From:** `main` after F4 · **Depends on:** F3, F4
- **Goal:** write the document outputs, detect completed documents, and write the run summary.
- **Functions:** `write_outputs(cfg, tool_id, doc_type, html, nodes, sections, assignment, verdict, temps, seeds, repair_rounds, usage)`, `document_complete(cfg, tool_id, doc_type) -> bool`, `write_run_summary(log_dir, summary)`
- **Files:** `phase1/outputs.py`, `phase1/datatypes.py` (`Verdict`), `tests/test_outputs.py`
- **Steps:**
  1. `write_outputs` (HTML first, meta last, planted `verified`/`not_verified`, `unintended` list, `usage` totals) → `feat(outputs): Write document HTML and metadata`
  2. `document_complete` → `feat(outputs): Detect completed documents`
  3. `RunSummary` (incl. `usage`) + `write_run_summary` → `feat(outputs): Write run summary`
- **Local test:** `tmp_path` data dir with a fixture verdict and fixture usage totals (no dependency on F7: `write_outputs` writes the totals it is given). Meta has every §4 field. A document counts as complete only when all three files exist. The summary flags a doc with a `not_verified` or unintended issue and shows usage per model.
- **Real API:** none.
- **Done:** files match §5 layout; no issue info appears in the HTML or TOC.

### F6 `feat/validator`
- **From:** `main` after F5 · **Depends on:** F1, F3, F4
- **Goal:** standalone `python validate.py data/` report.
- **Functions:** `validate_data_dir(data_dir) -> Report`, `validate_html_file(path, toc) -> list[str]`
- **Files:** `validate.py`, `tests/test_validate.py`, `tests/fixtures/data/tool1/{tool.json,toc_*.json,*.html,meta_*.json}`
- **Steps:**
  1. `validate_html_file` → `feat(validate): Validate HTML file against its TOC`
  2. `validate_data_dir` + per-file PASS/FAIL + exit code → `feat(validate): Add standalone data validator`
- **Local test:** `python validate.py tests/fixtures/data` prints PASS and exits 0. A `tmp_path` copy with a broken TOC, missing HTML, missing meta or bad `tool.json` prints FAIL with reasons and exits non-zero.
- **Real API:** none.
- **Done:** both cases above; the report names every failing file.

### F7 `feat/llm-client`
- **From:** `main` after F1 · **Depends on:** F1
- **Goal:** one OpenRouter call with strict `json_schema`, fixed provider routing, usage reporting, 429/402 handling, the attempt wrapper, and the usage ledger.
- **Functions:** `call_llm(model_cfg, messages, schema, temperature, seed) -> (dict, Usage)`, `with_attempts(label, produce, validate, ledger, max_attempts=cfg.retry.max_attempts) -> result`, `append_usage(ledger, label, attempt, ok, usage)`, `read_usage(path) -> list[UsageEntry]`, `sum_usage(entries) -> UsageTotals`, `run_usage(cache_dir, run_id) -> UsageTotals`; exceptions `BudgetExhausted`, `CallError` (carries `usage` when the call was billed), `GenerationFailed`
- **Files:** `phase1/llm.py`, `phase1/datatypes.py` (`Usage`, `Ledger`), `tests/test_llm.py`, `tests/fixtures/responses/probe_*.json`
- **Steps:**
  1. `Usage`/`Ledger` + `append_usage`, `read_usage`, `sum_usage`, `run_usage` → `feat(llm): Add usage ledger`
  2. Exceptions + `with_attempts` (ledger entry for every attempt) → `feat(llm): Add attempt wrapper and errors`
  3. `call_llm` success path (payload with strict schema, reasoning, seed, `provider` block, usage; JSON parse → `CallError(usage)`) → `feat(llm): Call OpenRouter with strict JSON schema`
  4. 429 handling (Retry-After, backoff, `max_total_wait_s` → `BudgetExhausted`) and 402 → `BudgetExhausted` → `feat(llm): Handle rate limits and out of credit`
  5. Run the probe, save the raw response bodies, and add a test that replays them through the fake `requests.post` → `test(llm): Add recorded probe responses`
- **Local test:** monkeypatch `requests.post` and `time.sleep` with fake responses: 200 with usage, invalid JSON (usage still recorded), 500, 402, 429 with Retry-After, 429 without it, a wait-cap overflow, and "no endpoints available". The payload must contain `provider.order`, `allow_fallbacks: false` and `require_parameters: true`. 429s must not count as attempts, `BudgetExhausted` must pass through `with_attempts`, and every attempt (failed ones too) must land in the ledger with the right `run_id`. `sum_usage`/`run_usage` totals are checked on fixture ledgers.
- **Real API:** design §10 level 2, one manual probe per model with a tiny schema. The probe code is not committed; its raw response bodies (no headers, no key) are saved as `tests/fixtures/responses/probe_deepseek-v4.1-flash-1017.json` and `probe_gemma-4-31b-it.json` (D44). It confirms strict schema and seed on the listed providers (§9.1), whether DeepSeek honors `temperature` with reasoning on (§9.2: same prompt at 0.2 and 1.0), and the usage fields (`usage.cost`, reasoning tokens, `provider`; §9.7). You record the findings in `phase1_design.md` §9/Changelog.
- **Done:** fake-response tests green, including the replayed probe responses; a real call to each configured model returns schema-valid JSON and a ledger entry with tokens, cost and provider.

### F8 `feat/tool-ideation`
- **From:** `main` after F7 · **Depends on:** F1, F7
- **Goal:** generate all fictional tools in one call and persist `tool.json`.
- **Functions:** `load_or_generate_tools(cfg, prompts, run_id) -> dict[str, Tool]`, `generate_tools(cfg, prompts) -> (list[Tool], Usage)`, `validate_tools(tools, num_tools) -> list[str]`
- **Files:** `phase1/ideation.py`, `prompts/tool_ideation.yaml` (remove `prompts/.gitkeep`), `tests/test_ideation.py`
- **Steps:**
  1. `validate_tools` → `feat(ideation): Validate generated tools`
  2. Prompt YAML + `generate_tools` → `feat(ideation): Generate fictional tools in one call`
  3. `load_or_generate_tools` (reuse/write `tool.json`) → `feat(ideation): Reuse or generate tool descriptions`
- **Local test:** `fake_llm` returns fixture tools and a fake `Usage`. Check the count, case-insensitive duplicate names and empty fields. The attempt is written to `.cache/tool_ideation/usage.jsonl`. A second run reuses existing `tool.json` files without calling the LLM. The prompt loads through `load_prompts`.
- **Real API:** one call (5 tools). Check they are fictional and from clearly different categories. The resulting `data/tool*/tool.json` stays uncommitted until the dataset commit (Q15).
- **Done:** a real run writes 5 valid `tool.json` files; a rerun makes no call.

### F9 `feat/toc-generation`
- **From:** `main` after F8 · **Depends on:** F3, F7
- **Goal:** the reasoning model produces a flat TOC that passes `validate_toc`.
- **Functions:** `generate_toc(tool, doc_type, guide, temperature, seed, cfg, prompts) -> list[RawTocEntry]`
- **Files:** `phase1/toc.py`, `prompts/toc.yaml`, `tests/test_toc.py`
- **Steps:**
  1. `prompts/toc.yaml` (detailed, schema-only example, depth guidance) → `feat(toc): Add TOC generation prompt`
  2. `generate_toc` with strict `{entries:[{id,parent_id|null,title,description}]}` → `feat(toc): Generate flat TOC with reasoning model`
- **Local test:** `fake_llm` records messages. Check every guide field and `max_depth`/`leaf_range` are rendered and the schema is strict (`additionalProperties: false`, all fields required). Feed the fake output through `validate_toc` → `build_toc_tree`.
- **Real API:** 2–3 TOCs (different doc types) for one tool. Check they pass `validate_toc` and that depth > 2 shows up where it's realistic.
- **Done:** real TOCs validate and save as nested JSON.

### F10 `feat/section-generation`
- **From:** `main` after F9 · **Depends on:** F4, F7
- **Goal:** write one leaf section as HTML with tool + all earlier sections in the system prompt, and cache it.
- **Functions:** `generate_section(tool, doc_type, leaf, guide, nodes, sections, assigned_issue, temperature, seed, cfg, prompts) -> SectionResult`, `load_cached_sections(cache) -> dict`, `save_cached_section(cache, section_id, result)` (plus the `toc_outline`, `sections_so_far`, `issue_instruction` helpers named in §4)
- **Files:** `phase1/sections.py`, `prompts/section.yaml`, `tests/test_sections.py`
- **Steps:**
  1. Cache load/save → `feat(sections): Cache finished sections for resume`
  2. `toc_outline`, `sections_so_far`, `issue_instruction` → `feat(sections): Build section prompt context`
  3. `prompts/section.yaml` + `generate_section` → `feat(sections): Generate one section as HTML`
- **Local test:** the system prompt contains every earlier leaf, numbered and in order, and no later leaf. `issue_instruction` text comes from YAML (Q4). The schema is strict. Cache round-trip works.
- **Real API:** 3–4 consecutive sections of one real TOC, one of them with a planted issue. All pass `validate_section`.
- **Done:** real sections validate; a rerun loads them from `.cache/` without calls.

### F11 `feat/judge`
- **From:** `main` after F10 · **Depends on:** F4, F5 (`Verdict`), F7
- **Goal:** the judge checks planted issues and finds unintended ones on the full document.
- **Functions:** `judge_document(tool, doc_type, html, nodes, sections, assignment, cfg, prompts) -> Verdict`, `validate_verdict(verdict, assignment, leaves) -> list[str]`, `sections_to_repair(verdict, assignment) -> list[str]`
- **Files:** `phase1/judge.py`, `prompts/judge.yaml`, `tests/test_judge.py`
- **Steps:**
  1. `validate_verdict` + `sections_to_repair` → `feat(judge): Validate verdicts and pick repairs`
  2. `prompts/judge.yaml` + `judge_document` → `feat(judge): Judge assembled document`
- **Local test:** a verdict missing a planted entry or with an unknown id fails. `sections_to_repair` returns ids in document order, without duplicates, and as the union of missing planted issues and unintended ones.
- **Real API:** one judge call on the F4 fixture document with known planted issues.
- **Done:** the real verdict passes `validate_verdict`, and the judge finds the fixture's planted issues.

### F12 `feat/repair`
- **From:** `main` after F11 · **Depends on:** F10, F11
- **Goal:** regenerate one section with the full document as context, and persist the repair round.
- **Functions:** `repair_section(tool, doc_type, leaf, guide, html, assigned_issue, unintended, temperature, seed, cfg, prompts) -> SectionResult`, `load_repair_round(cache) -> int`, `save_repair_round(cache, round)`
- **Files:** `phase1/judge.py`, `prompts/repair.yaml`, `tests/test_judge.py`
- **Steps:**
  1. Round counter persistence → `feat(judge): Persist repair round for resume`
  2. `prompts/repair.yaml` + `repair_section` → `feat(judge): Repair one section in full context`
- **Local test:** the prompt renders the full document and `fix_list`. The result goes through `validate_section`. A missing `repair_round.json` reads as 0.
- **Real API:** one repair call on a fixture section flagged by the F11 verdict.
- **Done:** the repaired section validates and the re-assembled document passes `validate_document`.

### F13 `feat/pipeline`
- **From:** `main` after F12 · **Depends on:** all
- **Goal:** `python generate.py config.yaml` runs the full §3 flow with resume and clean stops.
- **Functions:** `main(config_path)`, `generate_document(cfg, prompts, tool_id, tool, doc_type, guide, run_id) -> DocFlags`
- **Files:** `generate.py`, `tests/test_pipeline.py`, `README.md`, `CLAUDE.md` (Commands)
- **Steps:**
  1. `generate_document` TOC → sections → assembly (no judge yet) → `feat(pipeline): Generate one document end to end`
  2. Judge/repair loop → `feat(pipeline): Add judge and repair loop`
  3. `main`: dotenv, `run_id`, tools, selection, resume skip, `BudgetExhausted`/`GenerationFailed` stop, run summary with `run_usage`, logging to `logs/run_{timestamp}.log` → `feat(pipeline): Run all documents with resume`
  4. Run commands in README/CLAUDE.md → `docs: Add generate and validate commands`
- **Local test:** a scripted `fake_llm` that answers by schema, with a small `tmp_path` config (1 tool, 1 doc, `leaf_range` [4, 6], `issues_per_doc` [2, 2]). A full fake run writes outputs that pass `validate.py`. Raise `BudgetExhausted` mid-document, rerun, and check that cached sections and the repair round are reused, meta is written last, and meta usage covers both runs. A `GenerationFailed` run exits 1 with a summary.
- **Real API:** design §10 levels 3 and 4. First the smoke run, `python generate.py config.smoke.yaml` (2 tools × 2 documents, outputs under `smoke/`, ~$0.10–0.30), checked with `python validate.py smoke/data` and by reading the output; tune prompts and rerun as needed. Then the full run (~280–550 calls, estimated $1–1.5; resume only covers interruptions).
- **Done:** the smoke run passes the §10 checks; the real full run completes; `python validate.py data/` passes all 20 docs; the run summary lists flagged docs.

## 3. Order and dependency graph

Order: **F1 → F2 → F3 → F4 → F5 → F6** (no API) **→ F7 → F8 → F9 → F10 → F11 → F12 → F13**.

```
bootstrap
  └─ F1 config-loading
       ├─ F2 planning
       ├─ F3 toc-tree
       │    └─ F4 html-checks
       │         ├─ F5 outputs
       │         └─ F6 validator      (also F1, F3)
       └─ F7 llm-client
            ├─ F8 tool-ideation
            ├─ F9 toc-generation      (F3)
            ├─ F10 section-generation (F4)
            └─ F11 judge              (F4, F5)
                 └─ F12 repair        (F10)
                      └─ F13 pipeline (all)
```
F2, F3 and F7 only need F1. They can run in parallel (for example with your co-author) and
still merge in the listed order.

## 4. First feature: detailed start (F1 `feat/config-loading`)

```
git checkout main && git pull && git checkout -b feat/config-loading
```

**Step 1: required keys.** `phase1/config.py`: `load_config(path)` reads YAML, checks every
§6 key path, and returns `Config` with attribute access as used in §3.
`tests/test_config.py`: the real `config.yaml` loads; a copy without `retry.repair_rounds`
fails naming that key.
```
git add phase1/config.py tests/test_config.py
git commit -m "feat(config): Load config and check required keys" -m "Read config.yaml and fail with the full key path when any key from
the design config table is missing."
```

**Step 2: value ranges.** Same files. Check `docs_per_tool <= len(doc_types)`,
`issues_per_doc[1] <= len(issue_types)` and `min(leaf_range) >= issues_per_doc[1] + 1`.
Tests cover each violation.
```
git add phase1/config.py tests/test_config.py
git commit -m "feat(config): Check config value ranges" -m "Reject configs that ask for more document types or issue types than
exist, or a leaf range too small to hold every planted issue plus an
earlier leaf for a contradiction."
```

**Step 3: style guides.** `load_style_guides(guides_dir, doc_types)` checks the §5 fields
(`document_type`, `purpose`, `scope`, `core_topics`, `optional_topics`,
`tone_and_conventions`, `typical_length.section_words`). Tests: all 6 real guides load; a
missing file or field in `tmp_path` fails.
```
git add phase1/config.py tests/test_config.py
git commit -m "feat(config): Load style guides per document type" -m "Load one guide per configured document type and stop when a guide
or one of its required fields is missing."
```

**Step 4: prompt templates** (needs the Q7 placeholder syntax).
`load_prompts(prompts_dir)` loads `{system, user}` for `tool_ideation, toc, section, repair,
judge` and checks the required placeholders, which are derived from the §4 `render(...)`
calls. Tests use templates written to `tmp_path`: complete, missing file, missing
placeholder.
```
git add phase1/config.py tests/test_config.py
git commit -m "feat(config): Load prompt templates" -m "Load one system/user template per step and fail when a file or a
required placeholder is missing, so a broken prompt stops the run
before any API call."
```

**Verify:** `python -m pytest` is green. `python -c "from phase1.config import load_config, load_style_guides; c = load_config('config.yaml'); print(len(load_style_guides(c.paths.guides_dir, c.generation.doc_types)))"` prints `6`.

**Merge:**
```
git push -u origin feat/config-loading
gh pr create --base main --title "feat(config): Load config, guides and prompts" --body "Implements load_config, load_style_guides and load_prompts from phase1_design.md §4 Setup. Test: python -m pytest"
```
Merge on GitHub with **Create a merge commit**. Then:
```
git checkout main && git pull && git branch -d feat/config-loading
```
(Optional: in GitHub repo settings, allow only merge commits so squash and rebase can't be picked by accident.)

## 5. Requirements trace

| Design §2 requirement | Feature(s) |
|---|---|
| 20 docs = 5 tools × 4 docs | bootstrap `config.yaml`, F1, F13 |
| Types chosen from the 6 listed | F1, F2 |
| Output layout `/data/toolN/…` | F3 (`save_toc`), F5 (`write_outputs`) |
| TOC is a valid JSON object | F3 |
| Programmatic HTML parsing/validation | F4, F6 |
| Tool ideation: name, purpose, category, user base | F8 |
| Tools are fictional | F8 (prompt) |
| Random doc types per tool | F2 |
| Tool description is persistent context | F8 (`tool.json`), F9–F12 (passed to every call) |
| TOC by reasoning-capable model | bootstrap config, F9 |
| JSON via structured outputs | F7, plus schemas in F8–F12 |
| TOC deeper than 2 levels | F9 (prompt), F3 (`max_depth`) |
| Sections by cost-effective model, one by one | F10, F13 |
| Each section gets tool + all sections so far | F10 |
| At least two models | bootstrap config, F1 |
| Price/performance-based model choice | config (D1, D2, D30, D40), F7 (usage ledger), F5 (usage in meta and summary) |
| Temperature used and configurable, variety | F1, F7, F13 (per-doc sampling) |
| 2–3 intentional issues per document | F2 |
| Issues actually present | F4, F11, F12, F13 |
| Realistic length | F1 (guides), F3 (`leaf_range`), F4 (word count) |
| Sections HTML; assembled doc valid | F4 |
| No whole-document generation in one call | F10, F13 |
| Prompts in YAML | F1, F8–F12 |
| Detailed prompts | F8–F12 |
| No hard-coded fallbacks | F7, F13 |
| Configurable for all parameters | bootstrap config, F1 |
| Reproducible outputs | F2, F7 (`seed`, pinned snapshot, provider order), F5 (meta) |
| Basic HTML + JSON integrity validation | F6 |

Every requirement is covered.

## 6. Questions

**Blocking**
1. **Model IDs (§9.1).** *Resolved:* paid `deepseek/deepseek-v4.1-flash-1017` (ideation, TOC, judge) and `google/gemma-4-31b-it` (sections), each with a provider order (design D1–D3, D30, D39). The free Gemma endpoint has no strict structured outputs. The F7 probe confirms strict schema and seed in practice.
2. **Config inside `call_llm` / `with_attempts`.** The §4 signatures take no `cfg`, but they use `api.base_url`, `api.timeout_s`, `api.api_key_env`, `retry.backoff_base_s`, `retry.max_total_wait_s` and `retry.max_attempts`. How should these reach them? Blocks F7.
3. **Compliance slug.** §5 lists `compliance_certifications.yaml`, but the guide in the repo is `compliance_and_certifications.yaml` (same `document_type`). The plan uses `compliance_and_certifications`; you'd update the §5 text. OK?
4. **Shared prompt text.** Where do the `issue_instruction` text per issue type, the HTML contract text and `issue_type_definitions` live? §4 says each prompt file is `{system, user}`. Blocks F10–F12, not the order.
5. **`validate.py` limits.** `validate_data_dir(data_dir)` checks `depth <= max_depth`, but it gets no config. Should it read `config.yaml`? Blocks F6.
6. **Daily-limit error format (§9.5).** *Resolved:* not needed. Paid models have no daily cap; out of credits is HTTP 402 → `BudgetExhausted` (D32).
7. **Placeholder syntax.** The prompts contain JSON examples, so `str.format` needs doubled braces. The alternatives are `string.Template` (`$name`, stdlib) or Jinja2 (a new dependency). Blocks F1 step 4.

**Non-blocking (affect content, not order)**
8. **Temperature with reasoning (§9.2).** If the F7 probe shows DeepSeek ignores `temperature` with reasoning on, do you want to revisit D6?
9. **Defaults (§9.3).** The bootstrap uses the §6 values as written unless you change them.
10. **Daily cap (§9.4).** *Resolved:* paid models have no daily request cap (D30).
11. **Commit `style_guides/sources/`?** *Resolved:* no, it's ignored in B1.
12. **Unused guide fields.** `certification_profile` and `certification_catalog` (compliance guide) and `sources` (all guides) aren't rendered by `generate_toc` per §4, so they're ignored. Intended?
13. **Python version.** *Resolved:* keep 3.11+. Install Python 3.11 before creating the venv (the machine has 3.10.12).
14. **Names not in the design.** Package `phase1/`, `phase1/datatypes.py`, `tests/`, `tests/conftest.py`. OK? (`config.smoke.yaml`, `smoke/` and `tests/fixtures/responses/` are now in design §5/§10.)
15. **Allowed-tag list.** Should the §5 section HTML contract be a constant in `sections.py` or a config key?
16. **Dataset commit.** When do the generated `data/` files get committed? Proposed: one `chore(data): Add generated Phase 1 dataset` commit after F13's full run.
17. **Bootstrap without a PR.** Bootstrap commits go straight to `main` while features use PRs. OK?

