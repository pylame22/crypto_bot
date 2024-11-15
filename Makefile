run:
	uv run python -m app

format:
	uv run ruff format . 

lint:
	uv run ruff check . --fix
	uv run mypy .