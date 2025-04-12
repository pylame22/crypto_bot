run:
	uv run python -m src $(filter-out $@,$(MAKECMDGOALS))

load-data:
	uv run python -m src load-data

format:
	uv run ruff format src

lint:
	uv run ruff check src --fix
	uv run mypy src
