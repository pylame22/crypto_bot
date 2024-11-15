FROM python:3.12-alpine AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install uv

WORKDIR /app
COPY uv.lock pyproject.toml ./
RUN uv sync --frozen --no-dev

FROM base AS runner
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=base ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY src/ ./src
COPY .env ./
COPY config.yml ./

CMD ["python", "-m", "src"]