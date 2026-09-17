# Contributing

## Branching

- `main` is protected. Never commit to it directly (a pre-commit hook and a Claude Code hook both block this).
- Branch names: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`, `data/<slug>`, `eval/<slug>`.
- One PR per concern. Squash-merge; the PR title becomes the commit message.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org):

```
feat(extract): pdf-native path with one repair retry
fix(billing): monthly tier reset on season boundary
data(labels): gold records 011-020 verified, 4 corrections
eval(report): bill error by tariff type figure
docs(adr): evidence grounding instead of API citations
```

Scopes: `corpus`, `schema`, `extract`, `validate`, `billing`, `eval`, `report`, `prompts`, `labels`, `ci`, `docs`.

No AI attribution trailers. This repository has one human author; co-author lines naming an AI tool,
session URLs and "Generated with" badges are rejected by the commit-msg hook and by CI.

## Before opening a PR

```
make check          # lint + typecheck + tests, identical to CI
```

CI never calls an LLM or the network. Tests that do are marked `llm` / `network` and run locally only.

## Prompt work

Iterate on the dev split only. The test split (`labels/splits.json`) is scored once, at the end.

## Decisions

Anything that constrains future work (schema, metric definition, model choice, data handling) gets
an ADR in `docs/adr/`. Small, dated, immutable once accepted; supersede rather than edit.
