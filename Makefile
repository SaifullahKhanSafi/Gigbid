PYTHON ?= python
.PHONY: dev test eval seed demo lint
dev:
	$(PYTHON) -m scripts.start_local
seed:
	$(PYTHON) -m scripts.seed_data
test:
	$(PYTHON) -m pytest -q
eval:
	$(PYTHON) -m evals.runners.rag_eval
	$(PYTHON) -m evals.runners.decision_eval
	$(PYTHON) -m evals.runners.ablation
	$(PYTHON) -m evals.runners.agency_eval
	$(PYTHON) -m evals.runners.safety_eval
	$(PYTHON) -m evals.runners.gigsim_outcomes
demo:
	$(PYTHON) -m scripts.start_local --test-models
lint:
	$(PYTHON) -m ruff check .
