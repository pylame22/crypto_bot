FROM python:3.12-alpine AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    UV_VERSION=0.6.9 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \ 
    UV_PROJECT_ENVIRONMENT=/usr/local/

WORKDIR /app

# create appuser to run app
RUN addgroup -S appgroup \
    && adduser -S appuser -G appgroup \
    && mkdir -p /app/data/depth /app/data/agg_trade \
    && chown -R appuser:appgroup /app

FROM base AS builder

# install dependencies
RUN pip install --no-cache-dir "uv==$UV_VERSION" \
    && rm -rf /root/.cache/pip/*

COPY uv.lock pyproject.toml ./

# install poetry packages
RUN uv sync --frozen --no-dev

# copy app files to workdir
COPY ./src ./src
COPY .env ./
COPY config.yml ./

FROM base AS final

# copy dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/src ./src
COPY --from=builder /app/data ./data
COPY --from=builder /app/.env ./
COPY --from=builder /app/config.yml ./

# USER appuser

CMD ["python", "-m", "src"]
