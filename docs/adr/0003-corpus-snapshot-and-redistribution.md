# ADR 0003: Snapshot the corpus; redistribute PDFs as a release asset, not git objects

Date: 2026-09-15. Status: accepted.

## Context

Utility PDFs suffer link rot and silent in-place replacement (spec §2.2). The gold set is only
meaningful against the exact bytes that were verified.

## Decision

- `corpus/manifest.csv` (committed) records URL, retrieval timestamp, SHA-256, page count, bytes, and
  URDB id for every document.
- PDFs are stored under `corpus/pdfs/` (gitignored) and attached to a GitHub release as one archive.
- Three demo PDFs live in `corpus/demo/` and are committed so `make demo` works from a bare clone.
- `corpus fetch` refuses to overwrite a file whose hash differs from the manifest.

## Consequences

- The repo stays small; the gold set is reproducible from the release.
- A changed upstream PDF is detected, never silently absorbed.
