# ---- build stage: produce a wheel with uv's build backend ----
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS build

WORKDIR /src
COPY . .
RUN uv build --wheel --out-dir /dist

# ---- runtime stage: install the wheel that was just built ----
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

RUN groupadd --system quantumsolver \
    && useradd --system --gid quantumsolver --no-create-home quantumsolver

WORKDIR /app

COPY --from=build /dist/*.whl /tmp/
# Installs the quantumsolver package plus its runtime deps (Flask, qiskit, gunicorn, ...).
RUN uv pip install --system --no-cache /tmp/*.whl && rm /tmp/*.whl

COPY --chown=quantumsolver:quantumsolver gunicorn.conf.py .

# gunicorn.conf.py binds a unix socket here in addition to TCP 27100
RUN mkdir -p /run/quantumsolver && chown quantumsolver:quantumsolver /run/quantumsolver

USER quantumsolver

EXPOSE 27100

CMD ["gunicorn", "--config", "gunicorn.conf.py", "quantumsolver.app:app"]
