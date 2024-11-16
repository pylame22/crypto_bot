run:
	uv run python -m src

format:
	uv run ruff format . 

lint:
	uv run ruff check . --fix
	uv run mypy .