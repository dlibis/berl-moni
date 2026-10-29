from .master import master_bp
from .mailing_list import mailing_list_bp
from .notifier import notifier_bp
from .schedule import schedule_bp
from .status import status_bp
from .recovery import recovery_bp
from .auth_proxy import auth_proxy_bp
from .letters import letters_bp
from .export import export_bp
from .scheduler import scheduler_bp


def register_routes(app):
    app.register_blueprint(master_bp)
    app.register_blueprint(mailing_list_bp)
    app.register_blueprint(notifier_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(recovery_bp)
    app.register_blueprint(auth_proxy_bp)
    app.register_blueprint(letters_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(scheduler_bp)
