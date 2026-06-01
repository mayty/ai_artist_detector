.PHONY: db_shell
db_shell:
	uv run aiad db shell

.PHONY: redis_shell
redis_shell:
	uv run aiad redis shell

.PHONY: install
install:
	uv sync

.PHONY: stylecheck
stylecheck:
	uv run ruff format --diff --check .

.PHONY: style
style:
	uv run ruff format .

.PHONY: lintcheck
lintcheck:
	uv run ruff check .

.PHONY: lint
lint:
	uv run ruff check --fix --unsafe-fixes .

.PHONY: typecheck
typecheck:
	uv run pyrefly check .

.PHONY: check
check: stylecheck lintcheck typecheck

.PHONY: update_deps
update_deps:
	uv lock -U
	uv run python scripts/bump_pyproject.py

.PHONY: run_interactive
run_interactive:
	uv run aiad workers api-dev -p 8080

.PHONY: ingest
ingest:
	uv run aiad ingest all
