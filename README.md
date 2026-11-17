[![rbs](https://github.com/ReduxISU/quantumsolver/actions/workflows/rbs.yml/badge.svg)](https://github.com/ReduxISU/quantumsolver/actions/workflows/rbs.yml)

This is a flask application that will integrates with [Redux](https://github.com/ReduxISU/Redux) to provide qiskit based solvers
for problems.

**Python 3.12+ is required** (CI tests 3.12, 3.13 and 3.14). Dependencies and the environment are managed
with [uv](https://docs.astral.sh/uv/).

## Getting Started

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then sync the
environment (uv installs Python 3.14 automatically if it isn't already present):

```
cd the-location-of-this-README.md
uv sync
```

This creates `.venv/`, installs all runtime + dev dependencies, and installs the
`quantumsolver` package itself.

Run the development server. Redux expects the solver on port **27100**:

```
uv run flask --app quantumsolver.app run --port 27100
```

Or run it under gunicorn (the production WSGI server), binding TCP only:

```
uv run gunicorn --bind '[::]:27100' quantumsolver.app:app
```

> The committed `gunicorn.conf.py` additionally binds a unix socket at
> `/run/quantumsolver/gunicorn.sock` for nginx. That path is provisioned by systemd in
> production (see `deploy/`), so pass `--config gunicorn.conf.py` locally only if you first
> create it: `sudo mkdir -p /run/quantumsolver && sudo chown "$USER" /run/quantumsolver`.

## Running the Tests

```
uv run pytest -v
```

To match CI, run against both supported Python versions:

```
uv run --python 3.12 pytest -v
uv run --python 3.13 pytest -v
uv run --python 3.14 pytest -v
```

Lint (ruff) and format check (black):

```
uv run ruff check .
uv run black --check .
```

## CI and publishing

One workflow, `.github/workflows/rbs.yml`, runs the whole pipeline through the
[Redux Build System](https://github.com/ReduxISU/Redux_Build_System) inside this repo's devcontainer:
`audit → format-check → lint → unit-test (3.12, 3.13, 3.14) → build → integration-test → push`. Gates and
thresholds live in `rbs.toml`. The same command runs locally:

```
rbs ci
```

On a push to `main`, and only if every gate passed, `push` publishes the exact image the
integration tests ran against to `ghcr.io/reduxisu/quantumsolver` as `:<sha7>` and `:latest`. On
pull requests it reports `skipped`.

## API Endpoints

All solver endpoints accept `POST` with a JSON body and return a JSON object containing at minimum an `"answer"` field and a `"qasm"` field with the generated circuit.

Each solve runs in its own process. It is terminated, returning `{"answer": "timeout"}`, if it is
still running after 30 seconds, or as soon as the caller closes its connection (when running under
gunicorn), so an abandoned request doesn't keep a worker busy.

### `GET /health`
Returns `{"status": "ok"}`.

### `POST /deutsch-quantum`
Deutsch's algorithm. Determines whether a single-bit function is constant or balanced.

```json
[false, true]
```
The two booleans represent `[f(0), f(1)]`.

### `POST /deutsch-jozsa-quantum`
Deutsch-Jozsa algorithm. Determines whether an n-bit function is constant or balanced.

```json
{"nbits": 3, "f": [0, 1, 0, 1, 0, 1, 0, 1]}
```
`f` must have `2^nbits` entries, each `0` or `1`.

### `POST /bernstein-vazirani-quantum`
Bernstein-Vazirani algorithm. Recovers a hidden bitstring `s` from a function `f(x) = s·x mod 2`.

```json
{"nbits": 3, "f": [0, 1, 0, 1, 0, 1, 0, 1]}
```
`f` must have `2^nbits` entries encoding the dot-product oracle.

### `POST /sat-quantum`
Grover's algorithm. Finds a satisfying assignment for a boolean expression.

```json
{"boolexpr": "(x1 | !x2) & (x2 | x3)"}
```
Variables are any alphanumeric identifiers. Use `!` or `~` for NOT, `&` for AND, `|` for OR.

Response includes `"answer"` (e.g. `"(x1:True,x2:False,x3:True)"`), `"answer_bitstring"`, and `"qasm"`.

### `POST /prime-factorization-quantum`
Shor's algorithm. Prime-factorizes an integer (must be < 512).

```json
{"N": 15}
```

### `POST /maxcut-quantum`
QAOA (Quantum Approximate Optimization Algorithm). Finds a partition of a weighted undirected
graph's nodes into two non-empty sets S and T that maximizes the total weight of edges between them.

```json
{"nodes": ["1", "2", "3"], "edges": [["1", "2", 4], ["2", "3", 2], ["1", "3", 3]]}
```
Each edge is `[u, v, weight]`, or `[u, v]` for weight 1. Parallel edges are summed, self-loops are
ignored, and graphs are limited to 16 nodes. QAOA is approximate, so the cut is not guaranteed to be
the maximum. An optional `"seed"` (a non-negative integer, default 6680) seeds the simulator's
sampler, the only random step, so the same request always gets the same response.

Response includes `"answer"` (the S side in Redux certificate format, e.g. `"{1,3}"`), `"cut_weight"`,
`"answer_bitstring"` (one character per node, `1` = in S), `"seed"` (the seed used), and `"qasm"`. Invalid input returns
`{"error": ...}` with no `"answer"`.
