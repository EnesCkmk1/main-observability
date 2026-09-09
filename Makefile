PYTHON ?= python
.PHONY: setup dev test lint phoenix demo eval experiment failures seed down
setup:
	$(PYTHON) -m pip install -r requirements-dev.lock
	$(PYTHON) -m pip install --no-deps -e .
dev:
	$(PYTHON) -m uvicorn ai_observability_lab.api:app --reload --no-access-log
test:
	$(PYTHON) -m pytest -q
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m mypy
phoenix:
	docker compose up -d --build --wait
demo eval experiment failures seed:
	$(PYTHON) -m ai_observability_lab.cli $@
down:
	docker compose down
