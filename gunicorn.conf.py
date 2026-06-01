"""Gunicorn configuration for quantumsolver."""
# pylint: disable=invalid-name  # gunicorn requires lowercase config variable names
import multiprocessing

# Each request blocks for up to 25 s (internal timeout), so sync workers are correct.
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"

# Must exceed the 25-second in-app timeout so gunicorn doesn't kill a legitimately
# running solver before it has a chance to respond.
timeout = 30

bind = [
    "unix:/run/quantumsolver/gunicorn.sock",
    "[::]:27100",
]

# Log to stdout/stderr so systemd journal captures everything.
accesslog = "-"
errorlog = "-"
loglevel = "info"
