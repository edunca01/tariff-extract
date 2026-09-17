# ADR 0001: Two Anthropic models, one SDK, no abstraction layer

Date: 2026-09-15. Status: superseded by ADR 0004.

## Context

The spec (R2.7) requires a large/small model comparison. It does not require multiple vendors.

## Decision

Use the `anthropic` SDK directly. Large = `claude-opus-5`, small = `claude-haiku-4-5`, both set in
`config.toml`. No provider abstraction, no LiteLLM, no LangChain.

## Consequences

- PDF-native input and Pydantic structured output come from one SDK surface (`messages.parse`).
- Adding a Sonnet row is a config change. Adding another vendor is a deliberate v2 decision.
- Effort level is part of the configuration and is recorded in every result row.
