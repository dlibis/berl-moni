from flask import Flask

from common.config import require
from web.csrf import register_csrf
from web.routes import register_routes

require("web")
app = Flask(__name__)
register_csrf(app)
register_routes(app)
