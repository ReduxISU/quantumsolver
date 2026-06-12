[![build and unit tests](https://github.com/ReduxISU/quantumsolver/actions/workflows/main.yaml/badge.svg)](https://github.com/ReduxISU/quantumsolver/actions/workflows/main.yaml)

This is a flask application that will integrates with [Redux](https://github.com/ReduxISU/Redux) to provide qiskit based solvers
for problems.

**Python 3.10–3.13 is required.**

## Getting Started
To run this, create a python virtual environment and "enter" it

```
cd the-location-of-this-README.md
python3 -m venv .venv
```

For Windows:

```
.venv\scripts\Activate.bat
```

For anything else:

```
. .venv/bin/activate
```

Then install the requirements:

```
pip install -r requirements.txt
```

For development (adds pytest, pylint, pip-audit):

```
pip install -r requirements-dev.txt
```

Tell it which app we want:

For Windows:

```
set FLASK_APP=quantumsolver.py
```

For anything else:
```
export FLASK_APP=quantumsolver.py
```

Now, run it!

```
$ flask run
 * Serving Flask app 'quantumsolver.py'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

## Running the Tests

With the virtual environment active:

```
pytest -v
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
