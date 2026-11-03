# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

A 5-phase RAG system that helps software whitelisting teams check AI tools' legal and compliance documents. The full assignment is in `rag_htec_project_specification.md`. Read the relevant phase there before working on it.

1. **Data generation:** 20 synthetic HTML legal docs + JSON TOCs for 5 fictional tools
2. **Chatbot:** standalone console chatbot with persona, history, summary, and date tools
3. **Ingestion & search:** structure-aware chunking, embeddings, persisted vector index, top-K search with neighbour expansion
4. **Agentic RAG:** Phase 2 chatbot + retrieval tool, quoted citations, summarization at 60–70% of the context limit
5. **Evaluation:** golden dataset + DeepEval/TruLens metrics across configurations

Current state: Phase 1 is designed (`phase1_design.md`); no code exists yet.

## Key documents

- `rag_htec_project_specification.md`: the assignment (source of truth for requirements)
- `phase1_design.md`: Phase 1 flow, functions, config keys, numbered decisions (D1–D38), open questions
- `Yaml_file_generator_prompt.txt`: prompt for building `style_guides/*.yaml` from real public documents

When a design decision changes, update `phase1_design.md` (Decisions table and Changelog) together with the code.

## Tech stack

- Python 3.11+
- LLM access through OpenRouter's OpenAI-compatible chat completions API (`https://openrouter.ai/api/v1`); key in `OPENROUTER_API_KEY`
- Phase 1 models: Nemotron (reasoning: ideation, TOC, judge) and Gemma (cost-effective: sections). Exact model IDs are still an open question in the design doc
- `html5lib` for HTML validation

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
prompts/          # tool_ideation, toc, section, repair, judge (.yaml)
style_guides/     # one YAML per document type
data/toolN/       # tool.json, toc_*.json, *.html, meta_*.json
.cache/           # per-section resume cache (not committed)
logs/             # run logs and summaries (not committed)
validate.py       # standalone validator: python validate.py data/
```

Layout for phases 2–5 is not decided yet.

## Commands

None yet. Add setup, run, validate, and test commands here as they are implemented.

## Git

- Never `git add`, `commit`, or `push`, in either repo. The user commits everything.
- One branch per feature. Before starting work on a new feature, suggest a branch name in
  `type/short-name` form matching the commit type (e.g. `feat/models-baseline`) and the command
  to create it from an up-to-date `main`:
  `git checkout main && git pull && git checkout -b <branch>`.
  If the feature depends on an unmerged branch, branch from that one instead. Wait for the user
  to create the branch before editing files.
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

