from pathlib import Path

import pytest

from tariff_extract.config import load


def test_config_loads_three_model_rows() -> None:
    cfg = load(Path("config.toml"))
    assert set(cfg.models) == {"large", "small", "local"}
    assert cfg.models["large"].provider == "anthropic"
    assert cfg.models["local"].provider == "ollama"
    assert cfg.models["local"].num_ctx and cfg.models["local"].num_ctx >= 32768
    assert cfg.models["large"].key == "anthropic:" + cfg.models["large"].id
    assert cfg.extract.max_repairs == 1
    assert 0.0 < cfg.extract.evidence_min_ratio <= 1.0


def test_unknown_alias_is_an_error() -> None:
    with pytest.raises(KeyError):
        load(Path("config.toml")).models.resolve("medium")


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARIFF_CACHE_DIR", "/tmp/x")
    monkeypatch.setenv("TARIFF_LOCAL_MODEL", "gemma4:26b")
    monkeypatch.setenv("OLLAMA_HOST", "http://gpu-box:11434")
    cfg = load(Path("config.toml"))
    assert str(cfg.paths.cache) == "/tmp/x"
    assert cfg.models["local"].id == "gemma4:26b"
    assert cfg.ollama_host == "http://gpu-box:11434"
