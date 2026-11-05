# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

A 5-phase RAG system that helps software whitelisting teams check AI tools' legal and compliance documents. The full assignment is in `rag_htec_project_specification.md`. Read the relevant phase there before working on it.

1. **Data generation:** 20 synthetic HTML legal docs + JSON TOCs for 5 fictional tools
2. **Chatbot:** standalone console chatbot with persona, history, summary, and date tools
3. **Ingestion & search:** structure-aware chunking, embeddings, persisted vector index, top-K search with neighbour expansion
4. **Agentic RAG:** Phase 2 chatbot + retrieval tool, quoted citations, summarization at 60–70% of the context limit
5. **Evaluation:** golden dataset + DeepEval/TruLens metrics across configurations

## Current state (2026-11-05)

Phase 1 design and planning are finished and the local environment is ready. No feature code exists yet: `phase1/` holds only `__init__.py`, and `prompts/` and `tests/` are empty.

Done:
- **Bootstrap** (`201ebf8`, `a1b0c16`): `.gitignore`, `.env.example`, pinned `requirements.txt`, folder layout (`phase1/`, `prompts/`, `data/`, `tests/`), `config.yaml`, six style guides, generator prompts, README setup.
- **Plan:** `IMPLEMENTATION_PLAN.md` with features F1–F13 (branches, steps, tests, done criteria) and open questions.
- **Paid models** (`3bc2694`): DeepSeek V4.1 Flash for ideation, TOC and judge; Gemma 4 31B for sections. Also fixed provider routing, 402 as a clean stop, and a per-document usage ledger (D1–D3, D30–D32, D39–D41).
- **Testing** (`84e6b5d`): design §10 with four levels (unit tests with a fake LLM, model probe, smoke run, full run), committed `config.smoke.yaml`, probe responses kept as fixtures (D42–D44).
- **Code conventions:** D45 (`string.Template` placeholders, `$name`), D46 (`phase1/` package, shared types in `phase1/datatypes.py`, pytest layout), D47 (`Config` as nested frozen dataclasses). The compliance guide name is fixed to `compliance_and_certifications` everywhere. Plan Q3, Q7 and Q14 are resolved.
- **Environment:** Python 3.11.18 in `.venv`, all pinned packages installed, `.env` created.

Next steps:
1. Start F1 `feat/config-loading`. The user creates the branch: `git checkout main && git pull && git checkout -b feat/config-loading`. Then implement F1 step 1 (`Config` dataclasses + `load_config` with the required-keys check, design D47) as in `IMPLEMENTATION_PLAN.md` §4, followed by steps 2–4. Then F2–F6, which make no API calls.
2. Before F6: answer Q5 (where `validate.py` gets `max_depth`).
3. Before F7: buy OpenRouter credits, put the key in `.env`, and answer Q2 (how `call_llm` and `with_attempts` get the `api`/`retry` config).
4. Before F10: answer Q4 (where shared prompt text lives).

## Key documents

- `rag_htec_project_specification.md`: the assignment (source of truth for requirements)
- `phase1_design.md`: Phase 1 flow, functions, config keys, numbered decisions (D1–D47), open questions, testing (§10)
- `IMPLEMENTATION_PLAN.md`: bootstrap commits, feature branches F1–F13 with steps and done criteria, open questions
- `Yaml_file_generator_prompt.md`: prompt for building `style_guides/*.yaml` from real public documents
- `YAML_generator_compliance_and_certifications.md`: variant of that prompt for Compliance & Certifications

When a design decision changes, update `phase1_design.md` (Decisions table and Changelog) together with the code.

## Tech stack

- Python 3.11+
- LLM access through OpenRouter's OpenAI-compatible chat completions API (`https://openrouter.ai/api/v1`); key in `OPENROUTER_API_KEY`
- Phase 1 models (paid, through OpenRouter): `deepseek/deepseek-v4.1-flash-1017` (reasoning effort high: ideation, TOC, judge) and `google/gemma-4-31b-it` (reasoning off: sections, repairs). Requests use a fixed provider order with `require_parameters`; token usage and cost are recorded per document (design D1–D3, D30, D39–D41)
- `requests` (OpenRouter client), `html5lib` (HTML validation), `PyYAML`, `python-dotenv`, `pytest`; pinned in `requirements.txt`

## Rules from the specification

These are graded requirements. Do not break them.

- **Everything configurable:** models, temperature, counts, doc types, and retrieval params go in config files (`config.yaml`), never hard-coded.
- **Prompts live in YAML** (`prompts/*.yaml`, one per step), never as long inline strings. Prompts must be detailed, not minimal.
- **Structured outputs:** use strict `json_schema` response format for every JSON-producing LLM call.
- **No hard-coded fallbacks:** if an LLM call fails, retry, then stop with a clear error. Never substitute placeholder or default content.
- **Temperature must be used** and configurable.
- **Fictional tools only:** generate tool ideas in the pipeline so the LLM has no prior knowledge of them.
- **TOC:** saved as a real nested JSON object (not a string), and may go deeper than 2 levels.
- **Sections:** generated one at a time, always as HTML, with the tool description and all sections so far in the system prompt. The assembled document must be valid HTML.
- **Planted issues:** 2–3 per document, recorded only in `meta_*.json`, never in the TOC or HTML.
- **Citations (Phase 4):** answers must include direct quotes plus file/section source, not just summaries.
- **Phase 5 write-up:** the evaluation summary must be written by the user. Do not draft it.

## Coding style

The spec says submissions must not look entirely copilot-generated and must reflect the author's own engineering decisions. So:

- Follow the existing design docs; don't add features, abstractions, or files that aren't in the design without asking.
- Keep code plain and readable: small functions, clear names, few layers. Avoid boilerplate-heavy patterns and excessive comments or docstrings.
- When a choice isn't covered by the design, ask rather than pick silently.

## Layout (Phase 1, planned)

```
config.yaml
config.smoke.yaml # smoke run: 2 tools × 2 documents, outputs under smoke/ (not committed)
requirements.txt
generate.py       # entry point: python generate.py config.yaml
validate.py       # standalone validator: python validate.py data/
phase1/           # one module per design §4 group (config, llm, ideation, planning, toc, ...)
tests/            # pytest tests and fixtures (incl. recorded probe responses), no API calls
prompts/          # tool_ideation, toc, section, repair, judge (.yaml)
style_guides/     # one YAML per document type (sources/ is not committed)
data/toolN/       # tool.json, toc_*.json, *.html, meta_*.json
.cache/           # per-section resume cache (not committed)
logs/             # run logs and summaries (not committed)
```

Layout for phases 2–5 is not decided yet.

## Commands

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # set OPENROUTER_API_KEY
python -m pytest                  # tests, no API calls
```

Testing has four levels (unit tests, model probe, smoke run, full run); see `phase1_design.md` §10. Never test on free models (D42). Add the run, smoke-run and validate commands here once `generate.py` and `validate.py` are implemented.

## Git

- Never `git add`, `commit`, or `push`, in either repo. The user commits everything.
- One branch per feature. Before starting work on a new feature, suggest a branch name in
  `type/short-name` form matching the commit type (e.g. `feat/models-baseline`) and the command
  to create it from an up-to-date `main`:
  `git checkout main && git pull && git checkout -b <branch>`.
  If the feature depends on an unmerged branch, branch from that one instead. Wait for the user
  to create the branch before editing files.
- Exception while the project is still in the design and planning phase: design, docs and config
  changes with no feature code are made directly on `main`. Feature code always gets its own
  branch and PR.
- When a commit is due, give the exact files to `git add` and a runnable command:
  `git commit -m "type(scope): Subject" -m "Body"`.
- Message format: Conventional Commits (`feat|fix|docs|style|refactor|test|chore|exp`, where
  `exp` = experiment results), optional scope (e.g. `feat(data)`), imperative mood, capitalized
  subject, no trailing period, subject under 50 characters, body wrapped at 72 characters,
  explaining what and why.
- PLAN.md Section C is a reference schedule, not a strict one: adjacent commits may be combined
  and dates may shift, as long as each commit is one logical change, the history keeps ≥15
  commits from both authors, and it spans multiple days. Reword its sample messages to fit
  these rules.
  
## Code style
- Do not overengineer.
- Work incrementally with smaller steps. Validate each increment.
- Identify root cause before fixing issues. Prove with evidence (don't guess), then fix.
- Don't jump to conclusions. Don't apply workarounds.
- Prefer the optimized implementation when one exists, as long as it doesn't add needless abstraction.
- **Comments and docstrings** describe what the code does now, in the codebase's own voice.
  Never narrate the conversation ("as requested") or compare with a previous version ("now also…").
  Favor clear, concise docstring comments. Be sparing with comments outside docstrings.
  Keep README.md concise.

