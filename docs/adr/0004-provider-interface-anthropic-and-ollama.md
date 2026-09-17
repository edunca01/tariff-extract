# ADR 0004: Two providers behind one small interface: Anthropic API and local Ollama

Date: 2026-09-17. Status: accepted. Supersedes ADR 0001.

## Context

The project now compares a hosted model against a model served locally on the author's GPU
machine with Ollama. ADR 0001 chose a single vendor with no abstraction. Two providers with
different input mechanics (PDF bytes vs page images, `messages.parse` vs Ollama `format`) need a
seam, but not a framework.

## Decision

- `extract.providers` defines a `Provider` protocol with one method:
  `extract(doc, path, prompt, schema) -> ProviderResult` (raw JSON text, usage, latency).
- `AnthropicProvider`: PDF path sends the PDF as a `document` block; text path sends pdfplumber
  text; output via `client.messages.parse(output_format=TariffRecord)`; adaptive thinking with
  `effort` from config.
- `OllamaProvider` (`ollama` Python package, host from `OLLAMA_HOST`): PDF path renders pages to
  PNG with pdfplumber at `extract.render_dpi` and sends them as `images`; text path sends text;
  output via `format=TariffRecord.model_json_schema()`; `num_ctx` from config because Ollama's
  default context is too small for a 25-page document.
- Both paths land in the same Pydantic validation, the same validator, the same repair loop,
  the same cache. Cache key and result rows carry `provider:id`.
- `config.toml` holds three rows: `large` and `small` (Anthropic) and `local` (Ollama).
  The local tag is overridable with `TARIFF_LOCAL_MODEL`.
- No LangChain, LiteLLM, or OpenAI-compatible shim. Two classes, one protocol.

## Consequences

- The results table gains a `local` row per path. Its cost column is $0.00 API spend, so latency
  per document is reported next to cost for every row, or the comparison is misleading.
- "PDF-native" means different things per provider (bytes vs images). The README says so.
- Local models may need their own prompt wording to hit the schema. Prompts stay shared
  unless the dev split shows a provider-specific failure; then a provider-specific prompt file
  is added and hashed like any other.
- Default local model is `gemma4:12b` (vision, 7.6 GB). Larger cards should use `gemma4:26b`.
