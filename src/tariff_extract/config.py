"""Runtime configuration loaded from config.toml. Model is config, not code."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, RootModel

Provider = Literal["anthropic", "ollama"]


class ModelSpec(BaseModel):
    provider: Provider
    id: str
    effort: str | None = None  # anthropic only
    num_ctx: int | None = None  # ollama only

    @property
    def key(self) -> str:
        """Stable identifier used in cache keys and result rows."""
        return f"{self.provider}:{self.id}"


class Models(RootModel[dict[str, ModelSpec]]):
    def resolve(self, alias: str) -> ModelSpec:
        """Map a config alias (large|small|local) to its spec."""
        try:
            return self.root[alias]
        except KeyError as e:
            raise KeyError(f"unknown model alias {alias!r}; known: {sorted(self.root)}") from e

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        return iter(self.root)

    def __getitem__(self, alias: str) -> ModelSpec:
        return self.resolve(alias)


class Extract(BaseModel):
    max_tokens: int = 16000
    max_repairs: int = Field(default=1, ge=0, le=1)
    evidence_min_ratio: float = Field(default=0.90, ge=0.0, le=1.0)
    render_dpi: int = Field(default=110, ge=50, le=300)


class Corpus(BaseModel):
    sector: str = "Residential"
    min_startdate: str = "2023-01-01"
    max_pages: int = 25
    candidates: int = 40
    target_gold: int = 30


class Paths(BaseModel):
    pdfs: Path = Path("corpus/pdfs")
    manifest: Path = Path("corpus/manifest.csv")
    labels_draft: Path = Path("labels/draft")
    labels_gold: Path = Path("labels/gold")
    splits: Path = Path("labels/splits.json")
    prompts: Path = Path("prompts")
    cache: Path = Path("cache")
    results: Path = Path("results")
    reports: Path = Path("reports")


class Config(BaseModel):
    models: Models
    extract: Extract = Extract()
    corpus: Corpus = Corpus()
    paths: Paths = Paths()

    @property
    def ollama_host(self) -> str:
        return os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def load(path: Path | None = None) -> Config:
    """Load config.toml, then apply the small set of env overrides listed in .env.example."""
    path = path or Path(os.environ.get("TARIFF_CONFIG", "config.toml"))
    with path.open("rb") as f:
        cfg = Config.model_validate(tomllib.load(f))
    if local := os.environ.get("TARIFF_LOCAL_MODEL"):
        cfg.models.root["local"].id = local
    if cache := os.environ.get("TARIFF_CACHE_DIR"):
        cfg.paths.cache = Path(cache)
    if results := os.environ.get("TARIFF_RESULTS_DIR"):
        cfg.paths.results = Path(results)
    return cfg
