"""`tariff` command line: corpus | extract | eval | report.

Sub-commands are registered here and implemented in their modules as they land (M0-M4).
"""

from __future__ import annotations

import typer

from tariff_extract import __version__
from tariff_extract.config import load

app = typer.Typer(no_args_is_help=True, add_completion=False)
corpus_app = typer.Typer(no_args_is_help=True, help="M0: select, fetch, draft-labels")
extract_app = typer.Typer(no_args_is_help=True, help="M2: run extraction on a split")
eval_app = typer.Typer(no_args_is_help=True, help="M3: score a split")
report_app = typer.Typer(no_args_is_help=True, help="M4: tables and figures")
app.add_typer(corpus_app, name="corpus")
app.add_typer(extract_app, name="extract")
app.add_typer(eval_app, name="eval")
app.add_typer(report_app, name="report")


@app.command()
def version() -> None:
    """Print version and the configured models."""
    cfg = load()
    rows = "  ".join(f"{alias}={cfg.models[alias].key}" for alias in cfg.models)
    print(f"tariff-extract {__version__}  {rows}")
