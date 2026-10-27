SYSTEM_PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python

.PHONY: install run debug clean lint check-map

install:
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r requirements-dev.txt

check-map:
	@if [ -z "$(MAP)" ]; then \
		echo "Usage: make run MAP=<map_file>" >&2; \
		exit 2; \
	fi

run: check-map
	@$(VENV_PYTHON) -m fly_in "$(MAP)"

debug: check-map
	$(VENV_PYTHON) -m pdb -m fly_in "$(MAP)"

clean:
	find fly_in tests -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	$(VENV_PYTHON) -m flake8 .
	$(VENV_PYTHON) -m mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs
