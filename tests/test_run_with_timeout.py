"""Tests for run_with_timeout: the solve timeout and aborting when the caller
closes its connection."""

import multiprocessing
import socket
import struct
import threading
import time

import pytest

from quantumsolver import routes
from quantumsolver.app import app as flask_app


# Solve targets run in a spawned child process, so they must be importable at
# module level.
def slow_target(queue, data):
    """Stands in for a long solve."""
    time.sleep(data["seconds"])
    queue.put({"answer": "finished"})


def fast_target(queue, data):
    queue.put({"answer": data["x"] * 2})


@pytest.fixture
def connection():
    """A connected pair: `server` plays gunicorn's client socket, `client` the caller."""
    server, client = socket.socketpair()
    yield server, client
    server.close()
    client.close()


def run(func, data, sock):
    """Call run_with_timeout in a request context, as a route would."""
    with flask_app.test_request_context(environ_overrides={"gunicorn.socket": sock}):
        return routes.run_with_timeout(func, data)


def test_client_gone_without_socket():
    """No socket (flask dev server, test client): never gone."""
    assert not routes.client_gone(None)


def test_client_gone_idle_connection(connection):
    server, _ = connection
    assert not routes.client_gone(server)


def test_client_gone_unread_data_is_not_a_close(connection):
    """A keep-alive caller's next request makes the socket readable but isn't
    a close, and peeking leaves the data unread."""
    server, client = connection
    client.sendall(b"GET /health")
    time.sleep(0.05)
    assert not routes.client_gone(server)
    assert server.recv(64) == b"GET /health"


def test_client_gone_after_close(connection):
    server, client = connection
    client.close()
    assert routes.client_gone(server)


def test_client_gone_after_reset():
    """A reset (RST) counts as gone too."""
    listener = socket.create_server(("127.0.0.1", 0))
    client = socket.create_connection(listener.getsockname())
    server, _ = listener.accept()
    # SO_LINGER with a zero timeout makes close() send RST instead of FIN.
    client.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    client.close()
    time.sleep(0.05)
    try:
        assert routes.client_gone(server)
    finally:
        server.close()
        listener.close()


def test_aborts_when_client_closes(connection):
    """Closing the connection mid-solve terminates the solve promptly."""
    server, client = connection
    threading.Timer(1.0, client.close).start()

    start = time.monotonic()
    result = run(slow_target, {"seconds": 20}, server)
    elapsed = time.monotonic() - start

    assert result == {"answer": "client closed connection"}
    assert elapsed < 5
    assert not multiprocessing.active_children()


def test_times_out(connection, monkeypatch):
    """A solve still running at SOLVE_TIMEOUT is terminated."""
    monkeypatch.setattr(routes, "SOLVE_TIMEOUT", 1)
    server, _ = connection

    start = time.monotonic()
    result = run(slow_target, {"seconds": 20}, server)

    assert result == {"answer": "timeout"}
    assert time.monotonic() - start < 5
    assert not multiprocessing.active_children()


def test_returns_answer_with_open_connection(connection):
    """An open connection doesn't disturb a normal solve."""
    server, _ = connection
    assert run(fast_target, {"x": 21}, server) == {"answer": 42}


def test_returns_answer_without_socket():
    """Without a socket the solve runs as before."""
    assert run(fast_target, {"x": 4}, None) == {"answer": 8}
