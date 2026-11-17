# The uv version is pinned so builds are repeatable; Dependabot (docker ecosystem) bumps it.
# ---- build stage: produce a wheel with uv's build backend ----
FROM ghcr.io/astral-sh/uv:0.13.9-python3.14-trixie-slim AS build

WORKDIR /src
COPY . .
# The wheel, plus the runtime deps pinned (with hashes) exactly as uv.lock has them. --locked fails the
# build if uv.lock is out of date with pyproject.toml (--frozen would export the stale lock silently).
RUN uv build --wheel --out-dir /dist \
    && uv export --locked --no-dev --no-emit-project -o /dist/requirements.txt

# ---- runtime stage: install the wheel that was just built ----
FROM ghcr.io/astral-sh/uv:0.13.9-python3.14-trixie-slim

RUN groupadd --system quantumsolver \
    && useradd --system --gid quantumsolver --no-create-home quantumsolver

WORKDIR /app

COPY --from=build /dist/ /tmp/dist/
# Runtime deps (Flask, qiskit, gunicorn, ...) at the versions in uv.lock, then the quantumsolver wheel
# alone, so nothing is resolved fresh from PyPI and the image matches what pip-audit checked.
RUN uv pip install --system --no-cache --require-hashes -r /tmp/dist/requirements.txt \
    && uv pip install --system --no-cache --no-deps /tmp/dist/*.whl \
    && rm -rf /tmp/dist

COPY --chown=quantumsolver:quantumsolver gunicorn.conf.py .

# gunicorn.conf.py binds a unix socket here in addition to TCP 27100
RUN mkdir -p /run/quantumsolver && chown quantumsolver:quantumsolver /run/quantumsolver

USER quantumsolver

EXPOSE 27100

CMD ["gunicorn", "--config", "gunicorn.conf.py", "quantumsolver.app:app"]
