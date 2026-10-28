PYTHON := python3
MAIN   := main.py
MAP    ?= maps/easy/01_linear_path.txt
ARGS   ?=

MYPY_FLAGS := --warn-return-any --warn-unused-ignores \
              --ignore-missing-imports --disallow-untyped-defs \
              --check-untyped-defs

.PHONY: install run debug clean lint lint-strict

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) $(MAIN) $(MAP) $(ARGS)

debug:
	$(PYTHON) -m pdb $(MAIN) $(MAP) $(ARGS)

lint:
	flake8 .
	mypy . $(MYPY_FLAGS)

lint-strict:
	flake8 .
	mypy . --strict

clean:
	rm -rf .mypy_cache
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type f -name '*.py[co]' -delete