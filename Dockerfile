# syntax=docker/dockerfile:1.7

FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install ".[dev,orchestration,analytics]"


FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    MCT_LOG_LEVEL=INFO \
    MCT_API_HOST=0.0.0.0 \
    MCT_API_PORT=8000 \
    MCT_DASHBOARD_PORT=8501 \
    MCT_DUCKDB_PATH=/app/data/serving/tisseo/2026-07-17_160355/mobility_control_tower.duckdb \
    AIRFLOW_HOME=/app/airflow

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system mct \
    && useradd --system --gid mct --home-dir /app --shell /usr/sbin/nologin mct

COPY --from=builder /opt/venv /opt/venv
COPY . .
COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && mkdir -p /app/data /app/airflow/logs /app/airflow/plugins /app/airflow/config \
    && chown -R mct:mct /app /entrypoint.sh

USER mct

EXPOSE 8000 8501 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import socket, os; s=socket.create_connection(('127.0.0.1', int(os.getenv('MCT_HEALTH_PORT', os.getenv('MCT_API_PORT', '8000')))), 5); s.close()"

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["api"]

