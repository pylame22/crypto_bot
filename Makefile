run:
	uv run python -m src

run-reader:
	uv run python -m src.reader

format:
	uv run ruff format . 

lint:
	uv run ruff check . --fix
	uv run mypy .