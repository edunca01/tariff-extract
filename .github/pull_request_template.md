## What

<!-- one or two sentences -->

## Why

<!-- link the issue, ADR, or spec section -->

## Checklist

- [ ] `make check` passes locally (CI makes no LLM or network calls)
- [ ] No model IDs hardcoded; `config.toml` only
- [ ] Prompt change? Iterated on the dev split only; test split untouched
- [ ] Gold label change? Row added to `labels/corrections.csv`
- [ ] Schema change? `TariffRecord` bumped, fixtures regenerated, ADR if it constrains v2
- [ ] No AI attribution trailers in the commits
