# RAG_project

An end-to-end Retrieval-Augmented Generation (RAG) system that helps software whitelisting teams verify AI tools faster.

Approving an AI tool for company-wide use means reading its legal and compliance documents (privacy policy, terms of service, DPA, SLA, and so on) to answer questions like *"Is the model trained on our data?"* or *"Which license tier lets an admin turn that off?"*. These documents vary in naming and structure, so a single review can take days. This project builds a semantic-search chatbot that answers such questions with cited evidence.

## Phases

The project is built incrementally in five phases.

| Phase | Component | What it does |
|---|---|---|
| 1 | **Data generation** | Generates 20 synthetic legal documents (5 fictional tools × 4 document types) as HTML with JSON tables of contents. Each document has 2–3 planted quality issues (contradictions, ambiguity, typos, inconsistent terms). |
| 2 | **Chatbot** | Console chatbot with a consistent persona, in-memory history, conversation summary, and tool calls (current date, add days to a date). Separate from Phase 1. |
| 3 | **Ingestion & semantic search** | Parses the Phase 1 HTML, chunks it along the document structure, embeds the chunks, and stores them in a vector index on disk. A console search tool returns top-K hits with scores, neighbour chunks, and source info. |
| 4 | **Agentic RAG assistant** | Extends the Phase 2 chatbot with retrieval as a tool. The assistant decides when to search, answers with direct quotes and source citations, and summarizes old turns when the context reaches 60–70% of the token limit. |
| 5 | **Evaluation** | Evaluates the assistant on a validated golden dataset with a framework such as DeepEval or TruLens: contextual precision/recall, context utilization, answer relevancy, faithfulness, and answer correctness, across several model and retrieval configurations. |

## Status

| Phase | Status |
|---|---|
| 1 – Data generation | Design and implementation plan done, implementation not started |
| 2 – Chatbot | Not started |
| 3 – Ingestion & search | Not started |
| 4 – Agentic RAG | Not started |
| 5 – Evaluation | Not started |

## Phase 1 overview

- **Pipeline:** tool ideation → TOC generation (reasoning model, strict JSON schema) → section-by-section HTML generation (cost-effective model) → assembly → judge and repair → validation.
- **Models:** DeepSeek V4.1 Flash (tool ideation, TOC, judge) and Gemma 4 31B (sections), both paid, accessed through OpenRouter. The API key is read from the `OPENROUTER_API_KEY` environment variable. Token usage and cost are recorded per document in `meta_*.json`.
- **Configuration:** everything (models, temperatures, number of tools, document types, retry limits) lives in `config.yaml`. Prompts live in `prompts/*.yaml`, never inline in code.
- **Output:**

  ```text
  data/
  ├── tool1/
  │   ├── tool.json                   # tool description
  │   ├── toc_privacy_policy.json     # nested table of contents
  │   ├── privacy_policy.html         # assembled document
  │   ├── meta_privacy_policy.json    # metadata + planted-issue answer key
  │   └── ...
  └── tool2/ ... tool5/
  ```

- **Validation:** `python validate.py data/` checks that every HTML and JSON file is well formed and matches its TOC.

See [`phase1_design.md`](phase1_design.md) for the full design.

## Setup

Requires Python 3.11+.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                # then set OPENROUTER_API_KEY in .env
```

## Usage

```bash
python -m pytest                    # run the tests (no API calls)
python generate.py config.smoke.yaml  # small paid smoke run, 2 tools × 2 docs (not implemented yet)
python generate.py config.yaml      # generate the dataset (not implemented yet)
python validate.py data/            # validate generated files (not implemented yet)
```

`generate.py` resumes where it stopped, so a run interrupted by a rate limit can be restarted with the same command.

## Documents

- [`rag_htec_project_specification.md`](rag_htec_project_specification.md): full assignment specification
- [`phase1_design.md`](phase1_design.md): Phase 1 design, decisions, and open questions
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): Phase 1 bootstrap, feature branches, and order of work
- [`Yaml_file_generator_prompt.md`](Yaml_file_generator_prompt.md): prompt used to build the per-document-type style guides from real public documents
- [`YAML_generator_compliance_and_certifications.md`](YAML_generator_compliance_and_certifications.md): variant of that prompt for Compliance & Certifications, whose sources are spread over many pages
