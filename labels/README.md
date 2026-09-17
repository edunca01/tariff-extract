# Labels

- `draft/<id>.json`: generated from URDB by `tariff corpus draft-labels`. Never hand-edited.
- `gold/<id>.json`: hand-verified against the snapshot PDF. Every change from draft is a row in
  `corrections.csv` (`id, field, urdb_value, pdf_value, page, note`).
- `splits.json`: `{"dev": [...], "test": [...], "demo": [...]}`. Fixed before any prompt work.
  Test-split documents are not opened during prompt iteration.
