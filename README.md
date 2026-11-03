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
| 1 – Data generation | Design done (`phase1_design.md`), implementation not started |
| 2 – Chatbot | Not started |
| 3 – Ingestion & search | Not started |
| 4 – Agentic RAG | Not started |
| 5 – Evaluation | Not started |

## Phase 1 overview

- **Pipeline:** tool ideation → TOC generation (reasoning model, strict JSON schema) → section-by-section HTML generation (cost-effective model) → assembly → judge and repair → validation.
- **Models:** accessed through OpenRouter. The API key is read from the `OPENROUTER_API_KEY` environment variable.
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
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt     # added once implementation starts
export OPENROUTER_API_KEY=...
```

Run instructions for each phase will be added as the phases are implemented.

## Documents

- [`rag_htec_project_specification.md`](rag_htec_project_specification.md): full assignment specification
- [`phase1_design.md`](phase1_design.md): Phase 1 design, decisions, and open questions
- [`Yaml_file_generator_prompt.txt`](Yaml_file_generator_prompt.txt): prompt used to build the per-document-type style guides from real public documents
