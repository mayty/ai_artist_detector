.PHONY: stylecheck
stylecheck:
	ruff format --diff --check .

.PHONY: style
style:
	ruff format .

.PHONY: lintcheck
lintcheck:
	ruff check .

.PHONY: lint
lint:
	ruff check --fix --unsafe-fixes .

.PHONY: typecheck
typecheck:
	pyrefly check .

.PHONY: check
check: stylecheck lintcheck typecheck

.PHONY: update_deps
update_deps:
	uv lock -U
	python /app/scripts/bump_pyproject.py
