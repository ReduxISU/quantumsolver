"""quantum solver flask app initialization"""

from flask import Flask

app = Flask(__name__)

# pylint: disable=wrong-import-position
from app import routes
