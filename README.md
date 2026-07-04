[![build and unit tests](https://github.com/ReduxISU/quantumsolver/actions/workflows/main.yaml/badge.svg)](https://github.com/ReduxISU/quantumsolver/actions/workflows/main.yaml)

This is a flask application that will integrates with [Redux](https://github.com/ReduxISU/Redux) to provide qiskit based solvers
for problems.

**Python 3.12+ is required** (CI tests 3.12 and 3.13). Dependencies and the environment are managed
with [uv](https://docs.astral.sh/uv/).

## Getting Started

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then sync the
environment (uv installs Python 3.13 automatically if it isn't already present):

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
```

Lint (ruff) and format check (black):

```
uv run ruff check .
uv run black --check .
```

## API Endpoints

All solver endpoints accept `POST` with a JSON body and return a JSON object containing at minimum an `"answer"` field and a `"qasm"` field with the generated circuit.

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
