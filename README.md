# tariff-extract

Extracting machine-readable electricity tariffs from US utility PDFs, evaluated by bill impact
against a hand-verified gold set.

> Status: scaffolding. No results yet. Plan and technology decisions: [`docs/scope.md`](docs/scope.md).
> Specification: [`docs/spec.md`](docs/spec.md).

## Results

_Filled in at M4. Six rows: PDF-native vs text-only × {large, small} hosted models and one local
model served by Ollama; median / P90 annual bill error, numeric accuracy, schedule cell accuracy,
hallucination rate, cost and latency per document._

## Why this problem

Tariffs drive solar, storage and EV economics. Utilities publish them as inconsistent PDFs, and the
OpenEI Utility Rate Database that downstream tools consume is maintained by hand.

## Reproduce

```
make setup      # uv sync + git hooks
make check      # lint, typecheck, tests; no API keys, no network
make demo       # eval on 3 committed documents from cached LLM responses; no keys
```

Full run (needs `OPENEI_API_KEY` and, for the hosted rows, `ANTHROPIC_API_KEY` in `.env`):

```
make corpus-select corpus-fetch draft-labels
# hand-verify labels/draft -> labels/gold, then
make extract eval report SPLIT=test MODEL=large PATH_=pdf
```

Local model row (a machine with a GPU and [Ollama](https://ollama.com) installed):

```
ollama pull gemma4:12b        # or gemma4:26b on a 48 GB+ card; set TARIFF_LOCAL_MODEL to match
make ollama-check             # server reachable, model pulled
make extract eval SPLIT=dev MODEL=local PATH_=pdf
```

Setting up on a fresh machine: install `uv` and `git`, clone, then `make setup`. `uv` downloads
Python 3.12 itself; `uv.lock` is cross-platform.

## Repo map

```
src/tariff_extract/   corpus | schema | extract | validate | billing | eval | report | cli
prompts/              versioned prompts; hash recorded in every result
labels/               draft/ (from URDB), gold/ (hand-verified), corrections.csv, splits.json
corpus/               manifest.csv, demo/ (3 PDFs); full corpus is a release asset
cache/                LLM responses keyed by (doc sha256, model, prompt hash, path)
docs/                 spec.md, scope.md, adr/
```

## Limitations and v2

Residential, single-schedule PDFs of ≤ 25 pages only. Riders and adjustment clauses are listed in
`notes_unmodeled`, not extracted. Locating the right pages inside a full tariff book is the natural
v2 and the hardest real-world version of this problem.

## License

Code: MIT. URDB data: CC0. Tariff PDFs are public regulatory documents redistributed for
reproducibility with source URL and hash in `corpus/manifest.csv`.
