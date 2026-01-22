This repository has been moved to [ReduxISU/quantumsolver](https://github.com/ReduxISU/quantumsolver) and will be maintained there from now on.

---

This is a skeleton proposal for a flask application that
will integrate with Redux to provide qiskit based solvers
for problems.

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

To interact with it, see the example [`testdeutsch.py`](testdeutsch.py)
