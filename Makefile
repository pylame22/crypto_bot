run:
	.venv/bin/python -m app

lint:
	.venv/bin/ruff check . --fix
	.venv/bin/mypy .