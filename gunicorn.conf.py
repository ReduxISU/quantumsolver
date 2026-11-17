"""Gunicorn configuration for quantumsolver."""

import multiprocessing

# Each request blocks for up to SOLVE_TIMEOUT (30 s, routes.py), so sync workers are correct.
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"

# Must exceed routes.SOLVE_TIMEOUT (30 s) so gunicorn doesn't kill a legitimately
# running solver before it has a chance to respond.
timeout = 35

bind = [
    "unix:/run/quantumsolver/gunicorn.sock",
    "[::]:27100",
]

# Log to stdout/stderr so systemd journal captures everything.
accesslog = "-"
errorlog = "-"
loglevel = "info"
