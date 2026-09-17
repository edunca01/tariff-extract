.DEFAULT_GOAL := help
.PHONY: help setup lint fmt typecheck test check ollama-check corpus-select corpus-fetch draft-labels extract eval demo report all clean

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## install deps and git hooks
	uv sync --all-groups --all-extras
	uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

lint: ## ruff check + format check (no changes)
	uv run ruff check .
	uv run ruff format --check .

fmt: ## ruff autofix + format
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## mypy strict
	uv run mypy

test: ## pytest with coverage; never calls an LLM or the network
	uv run pytest --cov --cov-report=term-missing -m "not llm and not network"

check: lint typecheck test ## everything CI runs

# ---- local model ----

OLLAMA_HOST ?= http://localhost:11434
LOCAL_MODEL := $(shell sed -n '/^\[models.local\]/,/^\[/p' config.toml | grep '^id' | cut -d'"' -f2)

ollama-check: ## confirm the Ollama server is reachable and the configured local model is pulled
	@curl -sf $(OLLAMA_HOST)/api/tags >/dev/null || { echo "Ollama not reachable at $(OLLAMA_HOST)"; exit 1; }
	@curl -s $(OLLAMA_HOST)/api/tags | grep -q '"name":"$(LOCAL_MODEL)"' \
	  && echo "ok: $(LOCAL_MODEL) is available at $(OLLAMA_HOST)" \
	  || { echo "model $(LOCAL_MODEL) not pulled. Run: ollama pull $(LOCAL_MODEL)"; exit 1; }

# ---- pipeline (needs keys for the anthropic rows; see .env.example) ----

corpus-select: ## pull URDB, apply filters + quotas -> corpus/candidates.csv (needs OPENEI_API_KEY)
	uv run tariff corpus select

corpus-fetch: ## download candidate PDFs -> corpus/pdfs/, write corpus/manifest.csv
	uv run tariff corpus fetch

draft-labels: ## URDB records -> labels/draft/<id>.json
	uv run tariff corpus draft-labels

MODEL ?= large   # large | small | local (see config.toml)
PATH_ ?= pdf
SPLIT ?= dev

extract: ## run extraction on one split (MODEL=large|small|local PATH_=pdf|text SPLIT=dev|test)
	uv run tariff extract run --split $(SPLIT) --model $(MODEL) --path $(PATH_)

eval: ## score a split -> results/*.parquet (same vars as extract)
	uv run tariff eval run --split $(SPLIT) --model $(MODEL) --path $(PATH_)

demo: ## eval on 3 committed docs from cached responses; no keys needed
	uv run tariff eval run --split demo --model large --path pdf --cache-only
	uv run tariff report build --split demo

report: ## tables + figures from results/ -> reports/
	uv run tariff report build --split test

all: corpus-select corpus-fetch draft-labels ## full pipeline (then hand-verify labels, then extract/eval/report)
	@echo "Now verify labels/draft -> labels/gold, then: make extract eval report"

clean: ## remove caches (not the LLM response cache)
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
