from common.env import load_env

load_env()  # before anything below reads the environment

from flask import Flask  # noqa: E402

from common.config import require  # noqa: E402
from web.csrf import register_csrf  # noqa: E402
from web.routes import register_routes  # noqa: E402

require("web")
app = Flask(__name__)
register_csrf(app)
register_routes(app)
