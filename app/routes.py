"""This is the flask router for the quantum solver app"""

import multiprocessing

from flask import request

import bernstein_vazirani_quantum
import deutsch_jozsa_quantum
import deutsch_quantum
import sat_quantum
import shors_quantum
from app import app

# pylint: disable=missing-function-docstring


@app.route("/")
@app.route("/index")
def index():
    return "Welcome to the quantum solver."


def deutsch_jozsa_target(queue, data):
    """solve using deutsch-jozsa's algorithm and put result in queue"""
    queue.put(deutsch_jozsa_quantum.solve(data))


@app.route("/deutsch-jozsa-quantum", methods=["POST"])
def solver_deutsch_jozsa_quantum():
    if not request.is_json:
        return "expected json input"
    data = request.json
    return run_with_timeout(deutsch_jozsa_target, data)


def bernstein_vazirani_target(queue, data):
    """solve using bernstein vazirani's algorithm and put result in queue"""
    queue.put(bernstein_vazirani_quantum.solve(data))


@app.route("/bernstein-vazirani-quantum", methods=["POST"])
def solver_bz_quantum():
    if not request.is_json:
        return "expected json input"
    data = request.json
    return run_with_timeout(bernstein_vazirani_target, data)


def deutsch_target(queue, data):
    """solve using deutsch's algorithm and put result in queue"""
    queue.put(deutsch_quantum.solve(data))


@app.route("/deutsch-quantum", methods=["POST"])
def solver_deutsch_quantum():
    """deuatch quantum endpoint"""
    if not request.is_json:
        return "expected json input"
    data = request.json
    return run_with_timeout(deutsch_target, data)


def sat_target(queue, data):
    """solve using grover's algorithm and put result in queue"""
    queue.put(sat_quantum.solve(data))


@app.route("/sat-quantum", methods=["POST"])
def solver_sat_quantum():
    """sat quantum endpoint"""
    if not request.is_json:
        return "expected json input"
    data = request.json
    return run_with_timeout(sat_target, data)


def shors_target(queue, data):
    """solve using shor's algorithm and put result in queue"""
    queue.put(shors_quantum.solve(data))


@app.route("/prime-factorization-quantum", methods=["POST"])
def solver_prime_factorization_quantum():
    """prime factorization quantum endpoint"""
    if not request.is_json:
        return "expected json input"
    data = request.json
    return run_with_timeout(shors_target, data)


def run_with_timeout(func, data):
    """run a function with a timeout using multiprocessing"""
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=func, args=(queue, data))
    process.start()
    process.join(25)

    if process.is_alive():
        process.terminate()
        process.join()
        return {"answer": "timeout"}

    if queue.empty():
        return {"answer": "no answer?"}
    return queue.get()
