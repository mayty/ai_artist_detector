.PHONY: ensure_venv
ensure_venv:
ifndef VIRTUAL_ENV
	$(error) "Python virtual env must be active"
endif
	uv sync --active --no-managed-python

.PHONY: stylecheck
stylecheck: ensure_venv
	ruff format --diff --check .

.PHONY: style
style: ensure_venv
	ruff format .

.PHONY: lintcheck
lintcheck: ensure_venv
	ruff check .

.PHONY: lint
lint: ensure_venv
	ruff check --fix --unsafe-fixes .

.PHONY: typecheck
typecheck: ensure_venv
	pyrefly check .

.PHONY: deadcheck
deadcheck: ensure_venv
	vulture --sort-by-size ai_artist_detector

.PHONY: check
check: stylecheck lintcheck typecheck deadcheck

.PHONY: update_deps
update_deps: ensure_venv
	uv lock -U
	python /app/scripts/bump_pyproject.py
