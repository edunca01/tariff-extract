# ADR 0002: Evidence lives in the schema; grounding is our validator's job

Date: 2026-09-15. Status: accepted.

## Context

Spec R2.1 wants `{page, quote}` evidence on every leaf. The Anthropic API offers a citations feature
for document blocks, but it cannot be combined with structured output (`output_config.format`),
which R2.2 relies on for schema enforcement.

## Decision

`Evidence` is a Pydantic model nested at every leaf of `TariffRecord`. The model self-reports page
and quote. `validate.grounding` checks each quote against the pdfplumber text of the cited page with
`rapidfuzz` partial ratio >= 0.90. A failed grounding is a validation error fed to the repair loop and
counted in the evidence-grounding metric.

## Consequences

- One request shape for both input paths.
- The grounding metric measures the model's honesty about sources, which is a result in itself.
- If citations ever become compatible with structured output, revisit; supersede this ADR.
