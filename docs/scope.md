# Scope and build plan

Companion to [`spec.md`](spec.md). The spec says *what*; this says *how, with what, in what order*.
Status: drafted 2026-09-15, revised 2026-09-17 for the local-model row and the target KPIs.

## 1. One-paragraph scope

Take 40 residential rate-schedule PDFs selected from OpenEI URDB, hand-verify 30 of them into a gold
set, extract each through two input paths (PDF-native, text-only) and three models (a large and a
small hosted model via the Anthropic API, and a local model served by Ollama), validate and repair the output, and report field accuracy plus the **annual bill error** the
extraction mistakes would cause on three synthetic load profiles. Deliverable is a public repo whose
README carries a six-row results table, one figure, an error gallery, and a `make demo` that
reproduces the numbers on three committed documents with no API keys.

Everything in spec §7 stays out: demand charges, tariff books, OCR, riders, fine-tuning, UI.

## 1a. Target KPIs and how each is measured

| KPI (as it will be stated) | Metric | Where it comes from |
|---|---|---|
| Extracted tiered/TOU rate structures into validated, citation-grounded JSON | Structure match, schedule cell accuracy, evidence grounding rate | `eval` on the test split |
| 30-tariff hand-verified gold set; **X% error rate in public URDB records** | Two numbers, both reported: (a) share of the 30 records with at least one *material* correction, (b) share of numeric fields corrected. *Material* = the correction changes the annual bill on any of the three load profiles, computed as `bill(draft) != bill(gold)`. (a) is the headline. | `labels/corrections.csv` + the bill calculator, at M1/M3 |
| **X% median bill error at $X.XX/doc**, PDF-native vs text-only | Median annual bill error across docs x profiles; mean cost per doc from usage logs; latency per doc. The quoted row is the cheapest configuration that meets the spec §5 targets, not the best-scoring one. | results Parquet, M3 |

The denominators are fixed here, before any label is verified, so the numbers cannot be shaped after the fact.

## 2. Technology decisions

| Concern | Choice | Why |
|---|---|---|
| Language / runtime | Python 3.12, `uv`, lockfile | Same as the sibling ERCOT repo; pdfplumber and pyarrow-free stack are all 3.12-clean. |
| Schema | Pydantic v2 | Doubles as the structured-output schema sent to the model and the on-disk JSON contract. |
| Hosted LLM client | `anthropic` SDK ≥ 1.0 | Native PDF `document` blocks (32 MB / 600 pages, far above the 25-page cap) and `client.messages.parse(output_format=Model)` for schema-enforced JSON. |
| Local LLM client | `ollama` Python package against an Ollama server (`OLLAMA_HOST`) | JSON-schema constrained output via `format=`, image input for vision models, `num_ctx` control. Ollama was chosen over vLLM because the author runs both and Ollama's model pull + structured output needs no serving config. See ADR 0004. |
| Local model | `gemma4:12b` default, `gemma4:26b` on larger cards | Vision-capable so the PDF-native (page image) path is possible; 256K context; one `ollama pull`. Overridable with `TARIFF_LOCAL_MODEL`. |
| Provider seam | One `Provider` protocol, two classes | The only abstraction in the repo. No LangChain/LiteLLM. |
| Large model | `claude-opus-5` | Current default large model. 1M context; a 25-page PDF is ~40–60k input tokens. |
| Small model | `claude-haiku-4-5` | Cheapest current model; 200K context is plenty. Gives the cost/accuracy row the spec asks for. `claude-sonnet-5` is a possible third row if time allows. |
| Thinking / effort | adaptive thinking, `output_config.effort` from config | Effort is a config knob per model, recorded in the result row. Default `high`. |
| PDF text (ablation path) | `pdfplumber` | Table-aware text extraction; also used for page count, text-layer detection, and the evidence-grounding text. |
| Evidence grounding | `rapidfuzz` partial ratio ≥ 0.90 | Fast, dependency-light fuzzy match of the model's quote against per-page text. |
| Corpus fetch | `httpx` | URDB API + PDF download with content-type and size checks. |
| Tabular results | `polars` → Parquet | Per-field results are wide and numerous; Parquet is what the spec asks for; polars needs no pandas. |
| CLI | `typer` | `tariff corpus|extract|eval|report` sub-apps map 1:1 to the spec's commands. |
| Figures | `matplotlib` (optional extra) | One figure for the README; keep it out of the core install. |
| Config | `config.toml` via stdlib `tomllib` | Model IDs, thresholds, quotas. No YAML dependency. |
| Lint / types / tests | `ruff`, `mypy --strict` with the pydantic plugin, `pytest` | Identical to the sibling repo so CI is boring. |
| CI | GitHub Actions: lint, typecheck, test, config-loads, gitleaks, attribution check | Keys are forced empty in the workflow so no test can reach an API. |

### Things deliberately not used

- **API citations** (`citations: {enabled: true}`): they cannot be combined with structured output, so
  evidence is a field in the schema and our validator grounds it. See ADR 0002.
- **Batch API**: 30 docs × 4 configurations is ~120 calls; the disk cache makes reruns free, so the
  50% batch discount is not worth the async plumbing.
- **A vendor-neutral LLM framework**: two providers need one protocol and two classes, not LangChain or LiteLLM.
- **Ollama's OpenAI-compatible endpoint**: the native API exposes `format=` schema and `num_ctx`; the shim hides both.
- **pandas / DuckDB**: polars covers the eval tables; DuckDB can be added for ad-hoc queries later.

## 3. Cost estimate (verify on two docs before the full run, spec §8.4)

Assumptions: 25-page PDF ≈ 50k input tokens on the PDF path (text + rendered pages), ≈ 15k on the
text path; ≈ 3k output tokens per extraction; 30% of docs need one repair call.

| Configuration | Calls | Approx. cost |
|---|---|---|
| Opus 5, PDF, 30 docs | ~40 | ~$15 |
| Opus 5, text, 30 docs | ~40 | ~$5 |
| Haiku 4.5, both paths | ~80 | ~$3 |
| gemma4 local, both paths | ~80 | $0 API; report seconds/doc |
| Dev-split prompt iteration (10 docs × ~8 rounds, Opus PDF) | ~100 | ~$30 |
| **Total** | | **~$50–60** |

Every response is cached by `(doc sha256, model, prompt hash, path)`, so an eval rerun costs $0.

## 4. Architecture

```
URDB API ──corpus select──▶ candidates.csv ──corpus fetch──▶ corpus/pdfs/ + manifest.csv
                                   │
                                   └──draft-labels──▶ labels/draft/*.json ──(human)──▶ labels/gold/*.json
                                                                                       + corrections.csv
                                                                                       + splits.json
corpus/pdfs/<id>.pdf
   ├─ pdf path:  anthropic → document block; ollama → page PNGs ─┐
   └─ text path: pdfplumber text (both providers) ───────────────┴─▶ Provider.extract(schema) ─▶ validate ─▶ (repair once) ─▶ results/<id>.json
                                            ▲                              │
                                       cache/ (hit? skip call)        cost + latency log
labels/gold + results ──eval──▶ per-field Parquet + bill(record, profile) ──report──▶ tables, figure, error gallery
```

Module boundaries (all under `src/tariff_extract/`):

| Module | Owns | Never does |
|---|---|---|
| `corpus` | URDB client, filter + quota stratification, PDF fetch, manifest, URDB→schema draft mapping | LLM calls |
| `schema` | `TariffRecord`, `Evidence`, shape validators (12×24) | I/O |
| `extract` | prompt loading + hashing, `Provider` protocol with Anthropic and Ollama implementations, both input paths, cache, repair loop, usage log | Scoring |
| `validate` | domain checks and evidence grounding; returns a list of errors the repair prompt can use | Mutation of the record |
| `billing` | three load profiles, `bill()` with tiers/TOU/seasons, hand-computed test cases | Anything LLM |
| `eval` | field matching, period identity resolution by rate, bill error, aggregation | Prompt access |
| `report` | README tables, figure, error gallery markdown | Reading gold beyond what eval emits |

## 5. Milestones and day plan

| Day | Milestone | Done when |
|---|---|---|
| 1 | **M0 corpus** | `make corpus-select corpus-fetch draft-labels` produces 40 candidates, a manifest with hashes, and 40 draft labels. Spec §8.1–8.2 verified and noted in ADR 0003. |
| 1–2 | **M1 gold set** | 30 gold records, `corrections.csv`, `splits.json` (10/20, stratified), discrepancy rate written down. Test split sealed before any prompt is written. |
| 2–3 | **M2 pipeline** | Schema, both providers, both paths, validator, repair loop, cache, usage log. Per-doc cost measured on 2 docs (spec §8.4). Prompt iteration on dev only. Local row developed on the GPU machine with `make ollama-check` green. |
| 3–4 | **M3 eval** | Bill calculator with 3 hand-computed tests; `make eval` writes Parquet; metrics per spec §5 by tariff type. Test split run once per configuration. |
| 4–5 | **M4 report** | `make report` and `make demo` work from cache alone; README per spec §9; error gallery of the 5 worst docs. Release with corpus PDFs attached. |

The gold set (M1) is budgeted at 40% of the effort and is the milestone most likely to slip. If it
slips, cut the candidate count, not the verification.

## 6. Repository hygiene (public, single human author)

| Layer | Mechanism | What it enforces |
|---|---|---|
| Claude Code settings | `.claude/settings.json` → `attribution: {commit: "", pr: "", sessionUrl: false}` | Claude Code never adds co-author, badge, or session-URL trailers. Committed, so it applies to any clone. |
| Claude Code hook | `.claude/hooks/guard-git.py` (PreToolUse on Bash) | Refuses commits with attribution trailers, commits on `main`, force-pushes, pushes to `main`, staging `.env` or `corpus/pdfs/`. |
| Claude Code hook | `.claude/hooks/format-python.sh` (PostToolUse on Edit/Write) | Ruff-fixes and formats every Python file as it is written. |
| Claude Code permissions | `deny: Read(.env*)` | The key file is never read into a session. |
| git commit-msg hook | `scripts/check-commit-msg.sh` via pre-commit | Same trailer check, independent of which tool wrote the commit. |
| git pre-commit hook | `scripts/check-split-discipline.sh` | Refuses a commit touching `prompts/` and a test-split gold label together. |
| pre-commit | ruff, gitleaks, conventional commits, no-commit-to-main, large-file guard | Standard hygiene. |
| CI | `attribution` job scans every PR commit | Last line of defence, visible on the PR. |
| CI | keys forced to empty strings | No test can reach an API, whatever its marker says. |
| GitHub | `CODEOWNERS`, PR template, dependabot, issue template for extraction errors | Review discipline. |

Recommended branch protection on `main` once the repo is created: require PR, require the `ci`
checks, disallow force-push, squash-merge only.

## 7. Data and licensing notes for the README

- URDB content is CC0 unless noted; record the retrieval date and API version in the manifest.
- Utility tariff sheets are public regulatory filings. They are redistributed as a release asset
  for reproducibility, with the source URL, retrieval timestamp, and SHA-256 in `corpus/manifest.csv`.
- Only the three demo PDFs are committed to git. Code is MIT.

## 8. Open items to verify on day 1 (spec §8)

1. URDB API version string and bulk export URL.
2. Live-PDF rate among recent approved residential records (widen `startdate` if < 30%).
3. Per-doc token counts and cost on two real PDFs, both paths, both models.
4. Whether `pdfplumber` table extraction is good enough on co-op layouts or whether the text path
   needs a simple table-to-markdown pass.
5. That `gemma4:12b` returns schema-valid JSON for the full `TariffRecord` under `format=` on two
   docs, and how many page images at 110 DPI fit in `num_ctx=65536`. If not, drop to text-only for
   the local row and say so.
