"""quantum solver flask app initialization"""

from flask import Flask

app = Flask(__name__)

# Imported for its side effect of registering routes on `app`.
from quantumsolver import routes  # noqa: E402, F401
