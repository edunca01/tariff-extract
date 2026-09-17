# CLAUDE.md — tariff-extract

## What this repo is

LLM extraction of US residential electricity tariff PDFs into URDB-shaped JSON, evaluated by the
**bill error** the extraction mistakes would cause, against a hand-verified gold set of 30
documents. The full specification is `docs/spec.md`; the build plan and technology
decisions are `docs/scope.md`. This is a public portfolio repository with one human author.

## Non-negotiables

1. **CI makes no LLM calls and no network calls.** Tests run against committed fixtures and cached
   responses only. Anything that needs a key is marked `@pytest.mark.llm` or `@pytest.mark.network`
   and deselected by `make test`.
2. **URDB is a draft label, not ground truth.** `labels/draft/` is machine-generated from URDB.
   `labels/gold/` is hand-verified against the snapshot PDF. Never copy draft to gold without
   verification, and record every correction in `labels/corrections.csv`.
3. **The test split is sealed.** `labels/splits.json` fixes 10 dev / 20 test before any prompt work.
   Do not open, print, or score test-split documents while iterating on prompts. A pre-commit hook
   refuses a commit that touches `prompts/` and a test-split gold label together.
4. **Model is config, not code.** Model IDs and providers live in `config.toml` (`large`, `small`, `local`). Never hardcode a model string or a host.
5. **Explicit nulls.** A field absent from the document is `null`. The prompt says so, the schema
   allows it, and the hallucination metric measures it.
6. **Every LLM response is cached** on disk keyed by `(doc sha256, model, prompt hash, path)`.
   Reruns must be free. Every eval result records the prompt hash.
7. **Secrets via environment only.** `OPENEI_API_KEY`, `ANTHROPIC_API_KEY`. Never read `.env` into
   the conversation; never commit it.
8. **No AI attribution in git history.** No `Co-Authored-By`, no session URLs, no "Generated with"
   badges in commits or PR descriptions. `.claude/settings.json` disables it, a Claude Code hook
   blocks it, a commit-msg hook rejects it, and CI checks it. Do not work around any of these.
9. **Corpus PDFs are a release asset.** Only `corpus/manifest.csv` and the three demo PDFs in
   `corpus/demo/` are committed. Never stage `corpus/pdfs/`.

## Layout

```
src/tariff_extract/
  corpus/    URDB pull, filtering + quotas, PDF fetch, manifest, draft labels
  schema/    Pydantic TariffRecord (+ Evidence on every leaf), URDB -> schema mapping
  extract/   LLM calls: pdf path, text path, cache, repair loop, cost log
  validate/  domain checks (12x24 schedules, tier monotonicity, ranges, evidence grounding)
  billing/   bill(record, profile) -> annual $, three synthetic load profiles
  eval/      per-field scoring, bill error, aggregation to Parquet
  report/    tables + figures for the README
  cli.py     `tariff` Typer app: corpus | extract | eval | report
prompts/     versioned prompt files; hash recorded in every result
labels/      draft/ gold/ corrections.csv splits.json
corpus/      manifest.csv, demo/ (3 PDFs), pdfs/ (gitignored)
cache/       LLM responses; cache/demo/ is committed for `make demo`
tests/       unit tests + fixtures; no network, no LLM
docs/        scope.md, adr/
```

## Conventions

- Python 3.12, `uv`, `ruff` (line length 100), `mypy --strict`, `pytest`. `make check` is what CI runs.
- Pydantic models are the schema. JSON on disk is always produced by `.model_dump_json()` and read by
  `.model_validate_json()`; never hand-build dicts.
- Money is `float` in `$/kWh` and `$/month`; kWh bounds are `float | None` (`None` = unbounded last tier).
- Schedules are `list[list[int]]` of shape 12x24, indexing `energy_periods`. Validate the shape
  in the model, not in callers.
- Two providers behind one `Provider` protocol (ADR 0004). Anthropic: PDF path is a `document`
  block, output via `client.messages.parse`; no prefill, no forced tool choice. Ollama: PDF path is
  page PNGs rendered by pdfplumber, output via `format=<json schema>`, `num_ctx` from config,
  host from `OLLAMA_HOST`. Nothing else knows which provider it is talking to.
- On the GPU machine, `make ollama-check` must be green before running the `local` row. Never
  assume a model is pulled; the check says which tag to pull.
- Evidence quotes are self-reported by the model and then grounded by the validator (fuzzy ratio
  >= 0.90 against the PDF text layer). API citations are not used because they cannot be combined
  with structured output (see `docs/adr/0002`).
- Conventional commits, scopes: `corpus`, `schema`, `extract`, `validate`, `billing`, `eval`,
  `report`, `prompts`, `labels`, `ci`, `docs`.
- Branch from `main`, one PR per concern, squash-merge. The hook refuses commits on `main`.
- Decisions that constrain future work get an ADR in `docs/adr/`.

## When working on prompts

Iterate on the **dev** split only (`make extract SPLIT=dev`, `make eval SPLIT=dev`). The test split
is run once, at the end, for the README table. If you believe a test-split document is mislabeled,
say so and stop; the human decides.
