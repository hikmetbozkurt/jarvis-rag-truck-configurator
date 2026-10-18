.PHONY: install data ingest serve frontend chat evaluate test lint typecheck check

install:
	pip install -e ".[dev]"
	cd frontend && npm install

data:
	cd data_generation && Rscript run_all.R

ingest:
	jarvis ingest

serve:
	jarvis serve --reload

frontend:
	cd frontend && npm run dev

chat:
	jarvis chat

evaluate:
	jarvis evaluate

test:
	pytest

lint:
	ruff check src tests
	ruff format --check src tests

typecheck:
	mypy
	cd frontend && npm run typecheck

check: lint typecheck test
