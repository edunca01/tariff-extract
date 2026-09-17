# Spec: LLM Extraction of Utility Tariff Rate Schedules

Working name: `tariff-extract`
Target effort: 3–5 focused days (the gold set is ~40% of it)
Status of facts below: verified Sep 2026 unless listed under §8 "Verify before build"

---

## 1. Problem definition

**Input:** a PDF rate schedule published by a US electric utility (e.g. "Schedule RS – Residential Service").

**Output:** a validated JSON record of the rate's billing structure: fixed charges, tiered/time-of-use energy rates, seasonal and hourly schedules, effective date. Every extracted value carries a page-level citation.

**Output schema is a subset of the OpenEI Utility Rate Database (URDB) schema.** This matters for three reasons: the schema is already designed by domain experts, it is what solar/storage/bill-analysis tools consume, and URDB records provide *candidate* labels for building the evaluation set.

**Headline metric:** the bill error that extraction mistakes would cause, not only field accuracy. A wrong digit in a tier rate matters more than a wrong rate name, and the metric should reflect that.

**Document type locked for v1:** residential rate schedules, single-schedule PDFs of ≤ 25 pages.
**Out of scope (v1):** commercial/industrial demand charges, full tariff books (hundreds of pages), riders and adjustment clauses beyond what's printed in the schedule, scanned/image-only PDFs, net metering rules.

---

## 2. Data sources

### 2.1 Primary: OpenEI U.S. Utility Rate Database (URDB)

- **What:** tariff records for most US utilities, collected and quality-controlled by Illinois State University for DOE, hosted on OpenEI (NLR).
- **Access:** `https://api.openei.org/utility_rates` with a free API key. Filter params used here: `sector`, `approved`, `effective_on_date`, `detail=full`, `limit` (≤500) + `offset`. A gzipped bulk JSON export also exists and is preferable for corpus selection (one download, no paging).
- **Fields that make this corpus work:**
  - `source`: direct link to the rate sheet → **the input document**
  - `sourceparent`: utility's rates page → fallback when `source` is dead
  - `approved`: `true` if verified by an expert
  - `startdate` / `enddate` / `supercedes`: vintage matching
  - `energyratestructure`, `energyweekdayschedule`, `energyweekendschedule`, `fixedchargefirstmeter`, `fixedchargeunits`, `mincharge`, `minchargeunits`: **candidate labels**
- **License:** OpenEI content is CC0 unless noted.

### 2.2 Documents: utility-hosted PDFs at URDB `source` URLs

Tariffs are public regulatory documents; utilities are required to publish current schedules. That makes the documents reliably *available*, but not reliably *stable*:

| Risk | Consequence | Mitigation (required) |
|---|---|---|
| Link rot | Corpus can't be rebuilt | Snapshot each PDF at selection time. Record URL, retrieval timestamp, SHA-256, page count in `corpus/manifest.csv`. Publish PDFs as a GitHub release asset. Optionally save each URL to the Wayback Machine. |
| Utility overwrote the PDF at the same URL with a newer tariff | URDB record and PDF describe different vintages | Compare effective date printed in PDF to URDB `startdate`. Mismatch → exclude from corpus or label from PDF only. |
| URDB transcription errors or omissions | Labels wrong | **URDB is a draft label, not ground truth.** Every gold record is hand-verified against the snapshot PDF (§3, M1). |
| Rate sheet is an HTML page, not PDF | Different pipeline | Filter to `Content-Type: application/pdf`. |

### 2.3 Corpus selection criteria (all must hold)

1. `sector = Residential`, `approved = true`, `enddate` empty, `startdate ≥ 2023-01-01`
2. `source` returns HTTP 200 with a text-layer PDF of ≤ 25 pages
3. PDF effective date matches URDB `startdate` (±1 billing cycle)
4. Diversity quotas across the 40 candidates:
   - ≥ 15 distinct utilities, ≥ 10 states
   - ~⅓ flat, ~⅓ tiered (inclining block), ~⅓ time-of-use
   - ≥ 5 with seasonal differences
   - Mix of investor-owned utilities and co-ops/municipals (layouts differ a lot)
5. Target: 40 candidates → **30 verified gold records** after exclusions

### 2.4 Load profiles for bill-impact metric

Three synthetic hourly residential profiles (8,760 h), defined in code and committed:
- **Low:** 500 kWh/month average, flat daily shape
- **Typical:** 1,000 kWh/month, evening-peak shape, summer +40%
- **High/TOU-sensitive:** 2,000 kWh/month, strong 4–9 pm peak

Synthetic is fine here. The profiles only need to exercise tiers and TOU periods, not represent a real customer. (Optional upgrade: NREL End-Use Load Profiles.)

---

## 3. Functional requirements

### M0 — Corpus build (day 1)
- **R0.1** `corpus select` pulls URDB (bulk or API), applies §2.3 filters 1–2, and outputs a candidate list stratified by §2.3 quotas.
- **R0.2** `corpus fetch` downloads PDFs, writes the manifest (URL, timestamp, SHA-256, pages, bytes), and never re-downloads a hash it already has.
- **R0.3** `corpus draft-labels` converts each URDB record into the project schema as `labels/draft/<id>.json`.

### M1 — Gold set (day 1–2, the part people underestimate)
- **R1.1** Manually verify each draft label against its PDF. Correct errors, and record every correction in `labels/corrections.csv` (field, URDB value, PDF value, page). Save as `labels/gold/<id>.json`.
- **R1.2** Record per document: tariff type (flat/tiered/TOU), seasonal y/n, layout notes (tables vs prose, multi-column).
- **R1.3 Split fixed before any prompt work:** 10 dev / 20 test, stratified by tariff type. The test set is not opened during prompt iteration.
- **R1.4** Report the URDB-vs-PDF discrepancy rate. It's a small finding in its own right and justifies the verification step.
  Two rates, defined before verification starts: (a) share of gold records with at least one *material* correction, where material means `bill(draft) != bill(gold)` on any load profile; (b) share of numeric fields corrected. (a) is the headline number.

### M2 — Extraction pipeline (day 2–3)
- **R2.1 Schema:** Pydantic models defined in §4. Every leaf value has an `evidence` object: `{page: int, quote: str}`.
- **R2.2 Primary path (PDF-native):** send the PDF directly to the LLM as a document input, with the schema enforced through tool use / JSON-schema-constrained output.
- **R2.3 Ablation path (text-only):** extract text with `pdfplumber` (tables preserved where possible) and send text only. Same schema and prompt.
- **R2.4 Validation layer:** after parsing, run domain checks:
  - Schedule matrices are exactly 12×24 and every index points to an existing period
  - Tier `max` values strictly increasing; last tier unbounded
  - Energy rates within $0.00–$1.00/kWh; fixed charge within $0–$100/month
  - Every `evidence.quote` actually appears in the PDF text layer (fuzzy match ≥ 0.9)
- **R2.5 Repair loop:** on validation failure, one retry with the validation errors fed back. Log whether the repair succeeded. No unbounded retries.
- **R2.6 Explicit nulls:** fields absent from the document must be `null`, not guessed. The prompt says this, and the eval measures it.
- **R2.7** Model is config, not code. Run at least two models (one large, one small) for a cost/accuracy comparison, plus one locally served model (Ollama) for a hosted-vs-local comparison. Local rows report latency per document alongside a $0 API cost.
- **R2.8** Log per document: input tokens, output tokens, cost, latency, validation pass/fail, repair used.

### M3 — Evaluation (day 3–4)
- **R3.1** `eval run --split test --model X --path pdf|text` writes per-field results to Parquet.
- **R3.2** Metrics in §5, computed per document and aggregated, broken down by tariff type.
- **R3.3** Bill calculator: `bill(tariff_record, load_profile) -> annual $`. Implements fixed charge, tiers (monthly reset), TOU periods, seasons. Unit-tested against 3 hand-computed bills.

### M4 — Reporting (day 4–5)
- **R4.1** `make report` produces the §9 tables and figures from eval outputs alone.
- **R4.2** Error gallery: 5 worst documents by bill error, with the field-level diff and a short diagnosis each.

---

## 4. Output schema (v1)

```
TariffRecord
  utility_name: str                         + evidence
  eia_id: int | None                        (from URDB, not extracted)
  rate_name: str                            + evidence
  sector: "Residential"
  effective_date: date | None               + evidence
  fixed_charge: {amount: float, units: "$/month"|"$/day"} | None   + evidence
  min_charge:   {amount: float, units: ...} | None                 + evidence
  energy_periods: list[Period]              # URDB energyratestructure
    Period.tiers: list[Tier]
      Tier: {max_kwh: float | None, rate_per_kwh: float, adj_per_kwh: float | None} + evidence
  weekday_schedule: int[12][24]             # index into energy_periods
  weekend_schedule: int[12][24]
  notes_unmodeled: list[str]                # riders/adjustments the doc mentions but schema doesn't capture
```

`notes_unmodeled` is deliberate. It lets the model say "there's a fuel adjustment rider here" without forcing it into a field, and it exposes scope limits honestly.

---

## 5. Evaluation metrics and acceptance criteria

All on the **20-document test split**, for the selected model/path.

| Metric | Definition | Acceptance target |
|---|---|---|
| **Annual bill error** (headline) | \|bill(extracted) − bill(gold)\| / bill(gold), median and 90th pct across docs × 3 profiles | Median < 2%, P90 < 10% |
| Numeric field accuracy | Match within ±0.5% relative (rates, charges, tier bounds) | ≥ 90% |
| Categorical/date accuracy | Exact match after normalization | ≥ 90% |
| Structure match | Correct number of periods and tiers per period | ≥ 85% of docs |
| Schedule cell accuracy | Share of 576 weekday+weekend cells mapping to the correct period (period identity resolved by rate matching) | ≥ 95% |
| Hallucination rate | Share of gold-`null` fields returned non-null | ≤ 5% |
| Evidence grounding | Share of quotes found in PDF text | ≥ 95% |
| First-pass validation rate | Share passing R2.4 without repair | Reported |
| Cost and latency per doc | Mean, from R2.8 logs | Reported |

**Comparisons required in the results table:** PDF-native vs text-only; large vs small model. Four rows total.

If targets are missed, the README reports the actual numbers and the dominant failure mode. A well-measured 85% is a better portfolio artifact than an unmeasured "works great".

---

## 6. Engineering requirements

- Python 3.11+, lockfile, `ruff`, `pytest`. CI runs schema, validator, and bill-calculator tests against committed fixtures. **CI makes no LLM calls.**
- LLM responses cached on disk keyed by (doc hash, model, prompt hash), so eval reruns are free and reproducible.
- Prompts are versioned files in `prompts/`, not inline strings. Every eval result records the prompt hash.
- Secrets via env vars only (`OPENEI_API_KEY`, LLM provider key).
- One-command reproduction: `make demo` runs eval on 3 committed docs using cached responses (no keys needed). `make all` runs everything.
- Repo layout:
  ```
  src/tariff_extract/{corpus,schema,extract,validate,billing,eval,report}/
  corpus/manifest.csv
  labels/{draft,gold}/  labels/corrections.csv  labels/splits.json
  prompts/
  tests/
  ```

---

## 7. Out of scope / explicit non-goals

Commercial/industrial demand charges, tariff books requiring page localization, OCR, riders and fuel adjustment clauses, fine-tuning, a web UI. Tariff-book page localization is the natural v2 and is the hardest real-world version of this problem; mention it in the README as such.

---

## 8. Verify before build (not confirmed in research)

1. Current URDB API version string (`version=latest` is safe) and the bulk export URL/format.
2. Share of approved, recent residential URDB records whose `source` is still a live PDF. If it's low (<30%), widen `startdate` or accept `sourceparent` navigation for a few docs.
3. Current PDF input limits (pages, MB) and structured-output mechanism for the chosen LLM API: check provider docs (for Claude: docs.claude.com PDF support and tool use pages).
4. Per-doc cost estimate on 2 docs before running the full set.

---

## 9. Final README scope

1. **Title + one-sentence claim.** E.g. "Extracting machine-readable electricity tariffs from utility PDFs, evaluated by bill impact against a hand-verified gold set."
2. **Headline results table.** Four rows (PDF vs text × large vs small model): median/P90 bill error, numeric accuracy, schedule accuracy, hallucination rate, cost/doc.
3. **One figure:** bill error distribution by tariff type (flat/tiered/TOU). Second: one annotated example, a PDF snippet next to the extracted JSON with evidence citations.
4. **Why this problem.** Tariffs drive solar/storage/EV economics; they're published as inconsistent PDFs; URDB is maintained by hand.
5. **Data and gold set.** Corpus selection criteria, manifest/snapshot approach, URDB as draft labels, verification process, and the **URDB-vs-PDF discrepancy rate**.
6. **Pipeline.** Schema, PDF-native extraction, validation checks, repair loop, evidence grounding. One small diagram.
7. **Evaluation design.** Why bill error is the headline, field-level metrics, dev/test split discipline.
8. **Error analysis.** Top failure modes from the error gallery (e.g. TOU schedules described in prose, seasonal month boundaries, tier units).
9. **Limitations and v2.** Residential only, single-schedule PDFs, riders ignored, tariff-book localization as the next problem.
10. **Reproduce.** `make demo` with cached responses, then full run with keys.
11. **Repo map.**
