---
name: writing-unit-tests
description: Use when writing or updating unit tests, adding coverage
  for new code, or fixing a bug that needs a regression test, in any
  phase of this repo. Covers the pytest layout, naming, the fake-LLM
  and boundary mocking policy, and what every test file must cover.
---

# Writing unit tests

## Framework and layout

- pytest only (pinned in `requirements.txt`); plain `assert`, `pytest.raises`,
  `tmp_path`, `monkeypatch`. No `unittest.TestCase` classes, no extra plugins
- Tests live in `tests/`, not next to the source: `phase1/toc.py` →
  `tests/test_toc.py`. Later phases follow the layout their own design doc
  decides; if it is not decided yet, ask before creating folders
- Shared fakes (fake `call_llm`, fake `requests.post`) go in `tests/conftest.py`;
  input files go in `tests/fixtures/`, recorded API responses in
  `tests/fixtures/responses/`
- Plain module-level `test_*` functions grouped by the function they test;
  use `@pytest.mark.parametrize` for a table of bad inputs instead of copies
- Load the real `config.yaml`, `config.smoke.yaml`, `style_guides/` and
  `prompts/` where the code reads them, so a broken key, guide or placeholder
  fails here instead of in a paid run. Broken variants are written to `tmp_path`

## What every test file must cover

1. The documented happy path, as described in the phase's design doc
2. Every error path: each custom exception (e.g. `ConfigError`) raised with
   `pytest.raises(..., match=...)` checking the message names the bad key,
   file or id
3. Boundary inputs that the function actually handles: for a configured limit
   (a range or a maximum in `config.yaml`), test the value at the limit and
   one past it
4. Failure never produces content: after retries are used up the code raises;
   no placeholder text, default document or partial file is written
5. Determinism: the same seed gives the same output; results don't depend on
   call order
6. If fixing a bug: write the failing regression test FIRST, show it failing,
   then fix the root cause

## Naming

- Test names state behavior, not implementation:
  `test_rejects_toc_deeper_than_max_depth`, never `test_toc_works`
- Regression and decision tests cite their source in a one-line docstring:
  the design decision (`"""D50: unknown config keys are rejected."""`) or
  the PR number

## Mocking policy

- Mock at system boundaries only: LLM and embedding APIs, HTTP, clock,
  environment variables. NEVER mock the module under test or its pure helpers
- LLM calls: modules call `llm.call_llm(...)` through the module, so the
  `fake_llm` fixture swaps it with one `monkeypatch.setattr` and returns
  scripted answers in the real return shape. Everything after the call
  (validation, retries, ledger, file writing) runs for real
- Testing the client itself: fake `requests.post` replaying recorded responses
  from `tests/fixtures/responses/`, plus scripted 200, invalid JSON, 402,
  429 with and without `Retry-After`
- No real network calls and no API key: a test must pass with
  `OPENROUTER_API_KEY` unset (`monkeypatch.delenv`)
- Filesystem: don't mock it; write to `tmp_path`. Never touch `data/`,
  `smoke/`, `.cache/` or `logs/`
- Time: never sleep. Patch `time.sleep` to record the requested waits;
  patch the date source for date tools instead of asserting on today
- Randomness: pass a seed or a seeded `random.Random`; don't patch `random`
- Use `monkeypatch` for every patch so it is undone after each test; never
  assign module attributes directly
- LLM-judged evaluation metrics (DeepEval, TruLens) are not unit tests; unit
  tests cover only the code that loads datasets and aggregates scores

## Before you finish

Run `python -m pytest` from the repo root inside `.venv` and include the final
summary line in your report. If a test fails, find the cause and fix the code
or the test; do not skip it, mark it `xfail`, or loosen the assertion. Check
every function you added or changed has a test for its happy path and each
error it raises. Do not stage or commit; give the user the files to `git add`.
